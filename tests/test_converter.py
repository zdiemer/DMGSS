import base64
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from convert import ConversionError, convert, load_rom
from server import MAX_REQUEST, application, sample_rom


class ConverterTests(unittest.TestCase):
    def test_rom_mapping_preserves_both_ends_and_padding(self):
        data = bytearray(sample_rom()); data[0] = 77; data[-1] = 88
        rom = load_rom(data, 'gb')
        self.assertEqual((rom.base, rom.end, rom.fill), (0, 32768, 0))
        self.assertEqual((rom.exceptions[0], rom.exceptions[32767]), (77, 88))
        self.assertNotIn(0x2000, rom.exceptions)
        self.assertEqual(load_rom(bytes([0, 0, 0x76]), 'raw').end, 0x103)

    def test_rejects_unsupported_shapes_and_cartridge_hardware(self):
        for data, format in [(b'', 'raw'), (bytes(4097), 'raw'), (b'\x76', 'gb'), (bytes(32769), 'gb'), (b'\x76', 'other')]:
            with self.subTest(format=format, size=len(data)), self.assertRaises(ConversionError):
                load_rom(data, format)
        for offset, value in [(0x147, 1), (0x148, 1), (0x149, 2), (0x143, 0xC0)]:
            data = bytearray(sample_rom()); data[offset] = value
            with self.subTest(offset=offset), self.assertRaises(ConversionError):
                load_rom(data, 'gb')

    def test_bounds_css_complexity_even_for_valid_size(self):
        data = bytearray(range(256)) * 128
        data[0x143] = data[0x147] = data[0x148] = data[0x149] = 0
        with self.assertRaisesRegex(ConversionError, 'too dense'):
            load_rom(data, 'gb')

    def test_all_engines_are_self_contained_and_metadata_is_text(self):
        for mode in ('portable', 'automatic', 'checkpoint', 'streaming'):
            with self.subTest(mode=mode):
                page = convert(b'\x76', '<script>alert(1)</script>.bin', 'raw', mode)
                self.assertNotIn('<script', page)
                self.assertNotIn('<link', page)
                self.assertNotIn('href="/', page)
                self.assertNotIn('TEST PASSED', page)
                self.assertIn("script-src 'none'", page)
                self.assertIn('Conversion uses Python outside the browser', page)
                self.assertIn('href=""', page)

    def test_nonzero_fill_is_not_dropped(self):
        rom = load_rom(bytes([255]) * 100 + bytes([0x76]), 'raw')
        self.assertEqual(rom.fill, 255)
        self.assertEqual(rom.exceptions, {356: 0x76})

    def test_cli_creates_file_but_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp) / 'demo.bin', Path(temp) / 'demo.html'
            source.write_bytes(b'\x76')
            command = [sys.executable, 'tools/convert.py', str(source), '--format', 'raw', '-o', str(output)]
            subprocess.run(command, check=True, capture_output=True)
            before = output.read_bytes()
            second = subprocess.run(command, capture_output=True)
            self.assertEqual(second.returncode, 2)
            self.assertEqual(output.read_bytes(), before)
            self.assertEqual(source.read_bytes(), b'\x76')


class ServerTests(unittest.TestCase):
    def request(self, body=b'', content_type='application/x-www-form-urlencoded', **override):
        environ = {'REQUEST_METHOD': 'POST', 'PATH_INFO': '/convert/', 'HTTP_HOST': 'dmgss.test',
                   'HTTP_ORIGIN': 'https://dmgss.test', 'CONTENT_LENGTH': str(len(body)),
                   'CONTENT_TYPE': content_type, 'wsgi.input': io.BytesIO(body), **override}
        result = {}
        def start(status, headers):
            result.update(status=status, headers=dict(headers))
        result['body'] = b''.join(application(environ, start))
        return result

    def reset_body(self, **values):
        return urlencode({'payload': base64.b64encode(b'\x76').decode(), 'name': 'demo.bin',
                          'format': 'raw', 'mode': 'portable', 'delivery': 'open', **values}).encode()

    def multipart(self, parts):
        body = b''
        for name, value, filename in parts:
            disposition = f'Content-Disposition: form-data; name="{name}"'
            if filename is not None: disposition += f'; filename="{filename}"'
            body += b'--test-boundary\r\n' + disposition.encode() + b'\r\n\r\n' + value + b'\r\n'
        return body + b'--test-boundary--\r\n'

    def test_native_multipart_upload_encodes_arbitrary_binary(self):
        body = self.multipart([('rom', sample_rom(), 'demo.gb'), ('format', b'gb', None), ('mode', b'portable', None), ('delivery', b'open', None)])
        result = self.request(body, 'multipart/form-data; boundary=test-boundary')
        self.assertEqual(result['status'], '200 OK')
        self.assertIn(b'name="payload"', result['body'])
        self.assertIn(b'<button class="reset"', result['body'])
        self.assertEqual(result['headers']['Cache-Control'], 'no-store')
        self.assertIn("script-src 'none'", result['headers']['Content-Security-Policy'])

    def test_download_has_no_server_reset_dependency(self):
        result = self.request(self.reset_body(delivery='download'))
        self.assertEqual(result['status'], '200 OK')
        self.assertEqual(result['headers']['Content-Disposition'], 'attachment; filename="dmgss-cartridge.html"')
        self.assertNotIn(b'name="payload"', result['body'])
        self.assertNotIn(b'action="/convert/"', result['body'])

    def test_rejects_duplicate_and_malformed_fields(self):
        bodies = [self.reset_body() + b'&mode=automatic', self.reset_body(mode='bogus'),
                  self.reset_body(payload='not base64!'), self.reset_body(delivery='bogus'),
                  self.reset_body() + b'&rom=x', self.reset_body() + b'&unknown=x']
        for body in bodies:
            with self.subTest(body=body[:30]):
                self.assertTrue(self.request(body)['status'].startswith('400'))
        duplicated = self.multipart([('rom', b'\x76', 'x.bin'), ('rom', b'\x76', 'y.bin')])
        self.assertTrue(self.request(duplicated, 'multipart/form-data; boundary=test-boundary')['status'].startswith('400'))
        self.assertTrue(self.request(b'broken', 'multipart/form-data; boundary=none')['status'].startswith('400'))

    def test_rejects_large_requests_before_reading(self):
        class Unreadable:
            def read(self, size): raise AssertionError('Oversized body must not be read')
        result = self.request(CONTENT_LENGTH=str(MAX_REQUEST + 1), **{'wsgi.input': Unreadable()})
        self.assertTrue(result['status'].startswith('400'))

    def test_cross_origin_post_is_rejected(self):
        self.assertTrue(self.request(self.reset_body(), HTTP_ORIGIN='https://elsewhere.test')['status'].startswith('403'))
        self.assertTrue(self.request(self.reset_body(), HTTP_ORIGIN='https://[')['status'].startswith('403'))

    def test_errors_do_not_echo_rom_or_markup(self):
        result = self.request(self.reset_body(mode='<script>bad</script>'))
        self.assertTrue(result['status'].startswith('400'))
        self.assertNotIn(b'<script>', result['body'])
        self.assertIn(b'role="alert"', result['body'])

    def test_form_sample_and_health_are_gettable(self):
        for path in ('/convert/', '/convert/sample.gb', '/healthz'):
            with self.subTest(path=path):
                self.assertEqual(self.request(REQUEST_METHOD='GET', PATH_INFO=path)['status'], '200 OK')
        sample = self.request(REQUEST_METHOD='GET', PATH_INFO='/convert/sample.gb')['body']
        self.assertEqual(len(sample), 32768)
        self.assertEqual(sample[0x100:0x103], b'\xc3\x50\x01')
        self.assertEqual(sample[0x104:0x134], bytes(48))  # No Nintendo logo bundled.

    def test_static_paths_cannot_escape_dist(self):
        for path in ('/../src/index.html', '/../tools/cpu.py', '/%2e%2e/src/index.html'):
            self.assertTrue(self.request(REQUEST_METHOD='GET', PATH_INFO=path)['status'].startswith('404'))


if __name__ == '__main__':
    unittest.main()
