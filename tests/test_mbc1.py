import base64
import hashlib
import json
from pathlib import Path
import random
import sys
import unittest
from urllib.parse import urlencode
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from convert import ConversionError, convert, load_rom
from mbc1 import sample_rom
from server import MAX_REQUEST


class MBC1Tests(unittest.TestCase):
    def test_supported_headers_and_exact_size_validation(self):
        for size, header in [(32768,0), (65536,1), (131072,2)]:
            data=bytearray(size);data[0x147:0x14A]=bytes([1,header,0])
            self.assertTrue(load_rom(data,'gb').mbc1)
            for bad in (data[:-1],data+b'\0'):
                with self.assertRaises(ConversionError):load_rom(bad,'gb')
            for offset,value in [(0x147,2),(0x147,3),(0x147,0x19),(0x149,2),(0x148,3)]:
                bad=bytearray(data);bad[offset]=value
                with self.assertRaises(ConversionError):load_rom(bad,'gb')
        data=bytearray(262144);data[0x147:0x14A]=bytes([1,3,0])
        with self.assertRaises(ConversionError):load_rom(data,'gb')

    def test_largest_dense_documents_and_reset_budget(self):
        data=bytearray(random.Random(20).randbytes(131072))
        data[0x143]=0;data[0x147:0x14A]=bytes([1,2,0])
        reset=urlencode({'payload':base64.urlsafe_b64encode(data).decode(),'name':'x'*80,
                         'format':'gb','mode':'checkpoint','delivery':'open'}).encode()
        self.assertLess(len(reset),MAX_REQUEST)
        for mode,limit in [('portable',32),('automatic',40),('checkpoint',104)]:
            with self.subTest(mode=mode):
                page=convert(data,'max.gb','gb',mode,online=True)
                self.assertLess(len(page.encode()),limit*1024*1024)
                self.assertNotIn('<script',page)
                self.assertNotIn('TEST PASSED',page)
        with self.assertRaisesRegex(ConversionError,'Dense ROMs require'):
            convert(data,'max.gb','gb','streaming')

    def test_upstream_sources_match_pinned_hashes(self):
        root=Path(__file__).parent/'vendor/mooneye/mbc1'
        manifest=json.loads((root/'manifest.json').read_text())
        self.assertEqual(manifest['commit'],'31510e12eea6286d36eea060a6adde755e1067aa')
        for name,checksum in manifest['files'].items():
            self.assertEqual(hashlib.sha256((root/Path(name).name).read_bytes()).hexdigest(),checksum)

    def test_original_sample_has_valid_header_without_logo(self):
        data=sample_rom()
        self.assertEqual(len(data),65536)
        self.assertEqual(data[0x104:0x134],bytes(48))
        self.assertEqual(data[0x147:0x14A],bytes([1,1,0]))
        self.assertEqual(data[0x14D],(-sum(data[0x134:0x14D])-25)&255)
        self.assertEqual(int.from_bytes(data[0x14E:0x150],'big'),(sum(data[:0x14E])+sum(data[0x150:]))&65535)
