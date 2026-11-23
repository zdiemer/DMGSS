import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from conformance import cases


class ConformanceDataTests(unittest.TestCase):
    def test_vendored_data_and_licenses_match_manifest(self):
        root = ROOT / 'tests/vendor'
        manifest = json.loads((root / 'manifest.json').read_text())
        for file, expected in manifest['outputs'].items():
            with self.subTest(file=file):
                self.assertEqual(hashlib.sha256((root / file).read_bytes()).hexdigest(), expected)

    def test_independent_case_coverage_and_adapter_contract(self):
        vectors = cases()
        self.assertEqual(len(vectors['mooneye']), 4096)
        self.assertEqual({(x['initial']['a'], x['initial']['f']) for x in vectors['mooneye']},
                         {(a,f) for a in range(256) for f in range(0,256,16)})
        raw = json.loads((ROOT / 'tests/vendor/sm83/alu.json').read_text())
        self.assertEqual(len(raw), 2560)
        for original, adapted in zip(raw, vectors['sm83']):
            self.assertEqual(adapted['name'], original['name'])
            for reg in ('a','b','c','d','e','f','sp'):
                self.assertEqual(adapted['initial'][reg], original['initial'][reg])
                self.assertEqual(adapted['final'][reg], original['final'][reg])
            self.assertEqual(adapted['initial']['pc'], 256)
            self.assertIn(adapted['final']['pc'], (257,258))
        coverage = {}
        for case in vectors['sm83']:
            coverage[case['opcode']] = coverage.get(case['opcode'], 0) + 1
        self.assertEqual(len(coverage), 80)
        self.assertEqual(set(coverage.values()), {32})

    def test_cb_adapter_preserves_independent_register_and_memory_results(self):
        vectors = cases()
        adapted = sum((vectors[f'cb{i}'] for i in range(4)), [])
        raw = json.loads((ROOT / 'tests/vendor/sm83/cb.json').read_text())
        self.assertEqual(len(raw), 8192)
        self.assertEqual(len(adapted), len(raw))
        coverage = {}
        for original, case in zip(raw, adapted):
            before, after = original['initial'], original['final']
            memory = dict(before['ram'])
            second = memory[(before['pc'] + 1) % 65536]
            coverage[second] = coverage.get(second, 0) + 1
            self.assertEqual((case['opcode'], case['byte']), (0xCB, second))
            self.assertEqual(case['final']['pc'], 258)
            memory_operand = second % 8 == 6
            for reg in ('a','b','c','d','e','f','h','l','sp'):
                if memory_operand and reg in ('h','l'):
                    self.assertEqual(case['initial'][reg], 192 if reg == 'h' else 0)
                    self.assertEqual(case['final'][reg], case['initial'][reg])
                else:
                    self.assertEqual(case['initial'][reg], before[reg])
                    self.assertEqual(case['final'][reg], after[reg])
            if memory_operand:
                address = before['h'] * 256 + before['l']
                self.assertNotIn(address, (before['pc'], (before['pc']+1)%65536))
                self.assertEqual(case['initial']['m49152'], memory[address])
                self.assertEqual(case['final']['m49152'], dict(after['ram'])[address])
        self.assertEqual(set(coverage), set(range(256)))
        self.assertEqual(set(coverage.values()), {32})

    def test_high_adapter_preserves_upstream_return_bytes_and_memory(self):
        raw = json.loads((ROOT / 'tests/vendor/sm83/high.json').read_text())
        vectors = cases()['high']
        self.assertEqual(len(raw), 384)
        self.assertEqual(len(vectors), len(raw))
        coverage = {}
        for original, case in zip(raw, vectors):
            before, after = original['initial'], original['final']
            memory, output = dict(before['ram']), dict(after['ram'])
            opcode = memory[before['pc']]
            coverage[opcode] = coverage.get(opcode, 0) + 1
            for reg in ('a','b','c','d','e','f','h','l'):
                self.assertEqual(case['initial'][reg], before[reg])
                self.assertEqual(case['final'][reg], after[reg])
            if opcode in range(0xC7,0x100,8):
                self.assertEqual(case['initial']['pc'], before['pc'])
                self.assertEqual(case['final']['pc'], after['pc'])
                self.assertEqual(case['initial']['sp'], 0xFFFE)
                self.assertEqual((case['final']['sp']-case['initial']['sp'])%65536,
                                 (after['sp']-before['sp'])%65536)
                for delta in (1,2):
                    address = (before['sp']-delta)%65536
                    self.assertEqual(case['initial'][f'm{0xFFFE-delta}'], memory[address])
                    self.assertEqual(case['final'][f'm{0xFFFE-delta}'], output[address])
            else:
                address = 0xFF00 + (memory[(before['pc']+1)%65536] if opcode in (0xE0,0xF0) else before['c'])
                self.assertTrue(0xFF80 <= address <= 0xFFFE)
                self.assertEqual(case['initial'][f'm{address}'], memory[address])
                self.assertEqual(case['final'][f'm{address}'], output[address])
                self.assertEqual(case['initial']['sp'], before['sp'])
                self.assertEqual(case['final']['sp'], after['sp'])
        self.assertEqual(set(coverage), {*range(0xC7,0x100,8),0xE0,0xF0,0xE2,0xF2})
        self.assertEqual(set(coverage.values()), {32})

    def test_interrupt_adapter_preserves_ime_delay_and_return_target(self):
        raw = json.loads((ROOT / 'tests/vendor/sm83/interrupts.json').read_text())
        vectors = cases()['interrupts']
        self.assertEqual(len(raw), 96)
        self.assertEqual(len(vectors), len(raw))
        coverage = {}
        for original, case in zip(raw,vectors):
            before, after = original['initial'], original['final']
            opcode = dict(before['ram'])[before['pc']]
            coverage[opcode] = coverage.get(opcode,0)+1
            self.assertEqual(case['initial']['ime'],before['ime'])
            self.assertEqual(case['final']['ime'],after['ime'])
            self.assertEqual(case['final']['ime-delay'],after.get('ei',0))
            for reg in ('a','b','c','d','e','f','h','l'):
                self.assertEqual(case['initial'][reg],before[reg])
                self.assertEqual(case['final'][reg],after[reg])
            if opcode == 0xD9:
                self.assertEqual(case['final']['pc'],after['pc'])
                self.assertEqual(case['initial']['sp'],0xC000)
                self.assertEqual(case['final']['sp'],0xC002)
                for delta in (0,1):
                    address=(before['sp']+delta)%65536
                    self.assertEqual(case['initial'][f'm{0xC000+delta}'],dict(before['ram'])[address])
                    self.assertEqual(case['final'][f'm{0xC000+delta}'],dict(after['ram'])[address])
            else:
                self.assertEqual(case['final']['pc'],257)
                self.assertEqual(case['initial']['sp'],before['sp'])
                self.assertEqual(case['final']['sp'],after['sp'])
        self.assertEqual(coverage,{0xF3:32,0xFB:32,0xD9:32})


if __name__ == '__main__':
    unittest.main()
