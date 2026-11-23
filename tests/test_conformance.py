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


if __name__ == '__main__':
    unittest.main()
