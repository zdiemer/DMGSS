"""Bounded WSGI converter; native HTML forms are its only browser client."""
import base64
import binascii
from email import policy
from email.parser import BytesParser
import html
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from build import ROOT
from convert import ConversionError, MAX_ROM, convert
from cpu import stack_rom
from dense_rom import sample_rom as dense_sample_rom

MAX_REQUEST = 65536
CSP = "default-src 'none'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'none'; connect-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"


def sample_rom():
    # Original demo, relocated behind the cartridge header. No Nintendo logo
    # or boot ROM is included; our CPU starts directly at 0100.
    data = bytearray(MAX_ROM)
    data[0x100:0x103] = bytes([0xC3, 0x50, 1])
    program = stack_rom()
    for offset in (7, 26):  # CALL operands inside the original Stack lab.
        program[offset] += 0x50
    data[0x150:0x150 + len(program)] = bytes(program)
    data[0x134:0x13F] = b'DMGSS STACK'
    data[0x14D] = (-sum(data[0x134:0x14D]) - 25) % 256
    return bytes(data)


def form_page(error=None):
    page = (ROOT / 'src/converter.html').read_text()
    message = '<div class="error" role="alert"><strong>Conversion failed</strong><p>' + html.escape(error) + '</p></div>' if error else ''
    return page.replace('<!-- ERROR -->', message).encode()


def fields_from_request(environ):
    try:
        length = int(environ.get('CONTENT_LENGTH', ''))
    except ValueError:
        raise ConversionError('A Content-Length header is required.')
    if not 0 < length <= MAX_REQUEST:
        raise ConversionError('Upload request exceeds the 64 KiB limit or is empty.')
    content_type = environ.get('CONTENT_TYPE', '')
    if len(content_type) > 256 or '\r' in content_type or '\n' in content_type:
        raise ConversionError('Invalid upload encoding.')
    body = environ['wsgi.input'].read(length)
    if len(body) != length:
        raise ConversionError('Upload was incomplete.')
    if content_type.split(';', 1)[0].strip().lower() == 'application/x-www-form-urlencoded':
        try:
            parsed = parse_qs(body.decode('ascii'), keep_blank_values=True, max_num_fields=6, strict_parsing=True)
            if any(len(v) != 1 for v in parsed.values()):
                raise ValueError()
            return {k: v[0].encode('utf-8') for k, v in parsed.items()}, None
        except (ValueError, UnicodeError):
            raise ConversionError('Invalid reset form.')
    message = BytesParser(policy=policy.default).parsebytes(
        ('Content-Type: ' + content_type + '\r\nMIME-Version: 1.0\r\n\r\n').encode('ascii', errors='replace') + body)
    if message.get_content_type() != 'multipart/form-data' or not message.is_multipart() or message.defects:
        raise ConversionError('Use the ROM upload form.')
    fields, filename = {}, None
    parts = list(message.iter_parts())
    if len(parts) > 5:
        raise ConversionError('Too many form fields.')
    for part in parts:
        name = part.get_param('name', header='content-disposition')
        if part.is_multipart() or part.defects or part.get_content_disposition() != 'form-data' or name in fields or not name:
            raise ConversionError('Malformed or duplicate upload field.')
        # Native form-data has no MIME transfer encoding; do not transform bytes.
        if part.get('Content-Transfer-Encoding'):
            raise ConversionError('Encoded file parts are not supported.')
        fields[name] = part.get_payload(decode=True)
        if part.get_filename() is not None:
            if name != 'rom':
                raise ConversionError('Choose one ROM file.')
            filename = part.get_filename()
    return fields, filename


def application(environ, start_response):
    def respond(status, body, kind='text/html; charset=utf-8', extra=()):
        start_response(status, [('Content-Type', kind), ('Content-Length', str(len(body))),
            ('Content-Security-Policy', CSP), ('X-Content-Type-Options', 'nosniff'),
            ('Referrer-Policy', 'same-origin'), ('Cache-Control', 'no-store'), *extra])
        return [] if environ.get('REQUEST_METHOD') == 'HEAD' else [body]
    path, method = environ.get('PATH_INFO', '/'), environ.get('REQUEST_METHOD', 'GET')
    if path == '/healthz' and method in ('GET', 'HEAD'):
        return respond('200 OK', b'ok\n', 'text/plain')
    if path == '/convert/sample.gb' and method in ('GET', 'HEAD'):
        return respond('200 OK', sample_rom(), 'application/octet-stream', [('Content-Disposition', 'attachment; filename="dmgss-stack.gb"')])
    if path == '/convert/dense.gb' and method in ('GET', 'HEAD'):
        return respond('200 OK', dense_sample_rom(), 'application/octet-stream', [('Content-Disposition', 'attachment; filename="dmgss-dense.gb"')])
    if path == '/convert/' and method in ('GET', 'HEAD'):
        return respond('200 OK', form_page())
    if path == '/convert/' and method == 'POST':
        origin = environ.get('HTTP_ORIGIN')
        try:
            permitted = not origin or (urlsplit(origin).netloc == environ.get('HTTP_HOST') and urlsplit(origin).scheme in ('http', 'https'))
        except ValueError:
            permitted = False
        if not permitted:
            return respond('403 Forbidden', form_page('Submit from this site’s upload form.'))
        try:
            fields, filename = fields_from_request(environ)
            if set(fields) - {'rom', 'payload', 'name', 'format', 'mode', 'delivery'}:
                raise ConversionError('Unexpected form field.')
            if ('rom' in fields) == ('payload' in fields):
                raise ConversionError('Choose one ROM file.')
            if 'payload' in fields:
                data = base64.b64decode(fields['payload'], altchars=b'-_', validate=True)
                filename = fields.get('name', b'Imported cartridge').decode('utf-8')
            else:
                data = fields['rom']
            if not data or not filename:
                raise ConversionError('Choose a non-empty ROM file.')
            format = fields.get('format', b'gb').decode('ascii')
            mode = fields.get('mode', b'portable').decode('ascii')
            delivery = fields.get('delivery', b'open').decode('ascii')
            if delivery not in ('open', 'download'):
                raise ConversionError('Choose Convert & run or Download HTML.')
            page = convert(data, filename, format, mode, online=delivery == 'open')
        except (ConversionError, UnicodeError, binascii.Error) as error:
            message = str(error) if isinstance(error, ConversionError) else 'Invalid file or form encoding.'
            return respond('400 Bad Request', form_page(message))
        headers = [('Content-Disposition', 'attachment; filename="dmgss-cartridge.html"')] if delivery == 'download' else []
        return respond('200 OK', page.encode(), extra=headers)
    if method not in ('GET', 'HEAD'):
        return respond('405 Method Not Allowed', b'Method not allowed', 'text/plain', [('Allow', 'GET, HEAD')])
    # Local development/CI serves static files here. Production nginx handles
    # these routes; only /convert/ is proxied to this worker.
    root = (ROOT / 'dist').resolve()
    requested = root / path.lstrip('/')
    if path.endswith('/'):
        requested /= 'index.html'
    try:
        requested = requested.resolve()
    except (OSError, ValueError):
        return respond('404 Not Found', b'Not found', 'text/plain')
    if root in requested.parents and requested.suffix in ('.html', '.css') and requested.is_file():
        kind = 'text/css; charset=utf-8' if requested.suffix == '.css' else 'text/html; charset=utf-8'
        return respond('200 OK', requested.read_bytes(), kind)
    return respond('404 Not Found', b'Not found', 'text/plain')
