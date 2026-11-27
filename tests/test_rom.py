"""Output budgets for worst-case ROM data; browser tests verify decoding."""
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from convert import ConversionError,convert,load_rom
from dense_rom import sample_rom


class DenseROMTests(unittest.TestCase):
    def test_worst_case_documents_remain_bounded_in_supported_modes(self):
        data=bytearray(random.Random(16).randbytes(32768))
        for address in (0x143,0x147,0x148,0x149):
            data[address]=0
        for mode in ('portable','automatic','checkpoint'):
            with self.subTest(mode=mode):
                document=convert(data,'dense.gb','gb',mode)
                self.assertLess(len(document.encode()),{'portable':12,'automatic':24,'checkpoint':96}[mode]*1024*1024)
                self.assertNotIn('<script',document)
                self.assertNotIn('<link',document)
                self.assertNotIn('TEST PASSED',document)

    def test_dense_streaming_is_rejected_before_generation(self):
        for data,format in [(sample_rom(),'gb'),(bytes(range(256))*16,'raw')]:
            with self.subTest(format=format), self.assertRaisesRegex(ConversionError,'Dense ROMs require Compatible'):
                convert(data,'dense',format,'streaming')

    def test_sparse_streaming_limit_is_inclusive(self):
        direct=bytes([1])*1024+bytes(3072)
        self.assertIn('Streaming · Chromium only',convert(direct,'sparse.bin','raw','streaming'))
        with self.assertRaisesRegex(ConversionError,'Dense ROMs require Compatible'):
            convert(bytes([1])*1025+bytes(3071),'dense.bin','raw','streaming')

    def test_repeated_dense_pages_keep_download_small(self):
        # Raw format avoids header edits breaking an otherwise identical page.
        data=bytes(range(256))*16
        document=convert(data,'repeated.bin','raw','portable')
        self.assertLess(len(document.encode()),8*1024*1024)

    def test_original_dense_sample_header_and_bounds(self):
        data=sample_rom()
        self.assertEqual(len(data),32768)
        self.assertEqual(data[0x104:0x134],bytes(48))
        self.assertEqual(data[0x147:0x14A],bytes(3))
        self.assertEqual(data[0x14D],(-sum(data[0x134:0x14D])-25)&255)
        self.assertEqual(int.from_bytes(data[0x14E:0x150],'big'),(sum(data[:0x14E])+sum(data[0x150:]))&65535)
        self.assertEqual(load_rom(data,'gb').data,data)
