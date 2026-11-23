#!/usr/bin/env python3
"""Reproduce pinned, licensed CPU vectors. Does not run an emulator."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PINS = {'mooneye': '31510e12eea6286d36eea060a6adde755e1067aa',
        'sm83': 'f9c30210245dd691661db39f5ace022c465ecc2f'}
OPCODES = [*range(0x80, 0xC0), 0xC6,0xCE,0xD6,0xDE,0xE6,0xEE,0xF6,0xFE,
           0x07,0x0F,0x17,0x1F,0x27,0x2F,0x37,0x3F]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in PINS:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    out = ROOT / 'tests/vendor'
    manifest = {'pins': PINS, 'sources': {}, 'outputs': {}}
    for name, revision in PINS.items():
        checkout = getattr(args, name)
        actual = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
        if actual != revision or subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain']):
            parser.error(f'{name} must be a clean checkout at {revision}')
        (out / name).mkdir(parents=True, exist_ok=True)
        shutil.copyfile(checkout / 'LICENSE', out / name / 'LICENSE')
    source = (args.mooneye / 'acceptance/instr/daa.s').read_bytes()
    manifest['sources']['mooneye/acceptance/instr/daa.s'] = sha(source)
    vectors = [[int(a,16), int(f,2)*16, int(b,16), int(g,2)*16]
               for a,f,b,g in re.findall(rb'^\.db \$([0-9a-f]{2}), %([01]{4}), \$([0-9a-f]{2}), %([01]{4})', source, re.M)]
    assert len(vectors) == len({(a,f) for a,f,_,_ in vectors}) == 4096
    (out / 'mooneye/daa.json').write_text(json.dumps(vectors, separators=(',', ':')) + '\n')
    counts = []
    for filename, opcodes, prefix in [('alu.json', OPCODES, ''), ('cb.json', range(256), 'cb '), ('high.json', [*range(0xC7,0x100,8),0xE0,0xF0,0xE2,0xF2], '')]:
        selected = []
        for opcode in opcodes:
            source = (args.sm83 / f'v1/{prefix}{opcode:02x}.json').read_bytes()
            manifest['sources'][f'sm83/v1/{prefix}{opcode:02x}.json'] = sha(source)
            candidates = json.loads(source)
            if filename == 'high.json':
                if opcode in range(0xC7,0x100,8):
                    # Keep PC (and the pushed return bytes) unchanged, in ROM.
                    candidates = [x for x in candidates if x['initial']['pc'] < 0x8000
                                  and x['initial']['pc'] not in {(x['initial']['sp']-1)%65536, (x['initial']['sp']-2)%65536}]
                else:
                    def address(x):
                        before = x['initial']
                        offset = dict(before['ram'])[(before['pc']+1)%65536] if opcode in (0xE0,0xF0) else before['c']
                        return 0xFF00 + offset
                    candidates = [x for x in candidates if 0xFF80 <= address(x) <= 0xFFFE
                                  and address(x) not in {(x['initial']['pc']+i)%65536 for i in range(2 if opcode in (0xE0,0xF0) else 1)}]
            # Preserve raw upstream records; relocation happens only in the fixture
            # adapter. Exclude instruction/data aliasing for the [HL] adapter.
            if opcode % 8 == 6 and (prefix or 0x80 <= opcode < 0xC0):
                candidates = [x for x in candidates if x['initial']['h']*256+x['initial']['l'] not in {(x['initial']['pc'] + i) % 65536 for i in range(2 if prefix else 1)}]
            # Include every observed output flag pattern, then earliest records to 32.
            chosen, flags = [], set()
            for case in candidates:
                if case['final']['f'] not in flags:
                    flags.add(case['final']['f']); chosen.append(case)
            for case in candidates:
                if len(chosen) == 32:
                    break
                if case not in chosen:
                    chosen.append(case)
            assert len(chosen) == 32
            selected.extend(chosen)
        (out / 'sm83' / filename).write_text(json.dumps(selected, separators=(',', ':')) + '\n')
        counts.append(len(selected))
    for file in ('mooneye/daa.json', 'mooneye/LICENSE', 'sm83/alu.json', 'sm83/cb.json', 'sm83/high.json', 'sm83/LICENSE'):
        manifest['outputs'][file] = sha((out / file).read_bytes())
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Imported {len(vectors)} hardware DAA cases and {sum(counts)} instruction vectors.')


if __name__ == '__main__':
    main()
