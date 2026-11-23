"""Test-only, independent single-instruction CSS fixtures; no Python emulation.

Initial state is fixed at generation time. Expected state is never emitted into
the browser document; Playwright only reads results with page JS disabled.
"""
import json
from pathlib import Path

from cpu import machine
from portable import storage
from rom import ROM

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 128
REGISTERS = ['pc','sp','a','b','c','d','e','f','h','l']


class FixtureROM(ROM):
    def __init__(self):
        super().__init__([0,0], compact=False)

    def lookup(self, key, choose, extra=None, valid=None):
        # These numeric inputs are encoded before loading, just like ROM bytes.
        return choose(key, {256:'var(--input-opcode)', 257:'var(--input-byte)', **(extra or {})}, 255)


def cases():
    result = {'mooneye': [], 'sm83': [], **{f'cb{i}': [] for i in range(4)}}
    for a,f,b,g in json.loads((ROOT / 'tests/vendor/mooneye/daa.json').read_text()):
        initial = {reg: 0 for reg in REGISTERS}
        initial.update(pc=256, a=a, f=f)
        final = {**initial, 'pc':257, 'a':b, 'f':g, 'ticks':1, 'fault':0, 'halted':0, 'm49152':0}
        result['mooneye'].append({'name':f'DAA A={a:02x} F={f:02x}', 'opcode':0x27, 'byte':0,
                                  'initial':initial, 'final':final})
    raw = json.loads((ROOT / 'tests/vendor/sm83/alu.json').read_text())
    raw += json.loads((ROOT / 'tests/vendor/sm83/cb.json').read_text())
    for case in raw:
        original = case['initial']
        memory = dict(original['ram'])
        opcode = memory[original['pc']]
        second = memory.get((original['pc']+1)%65536,0)
        initial = {reg: original[reg] for reg in REGISTERS}
        final = {reg: case['final'][reg] for reg in REGISTERS}
        initial['pc'] = 256
        final['pc'] = 256 + ((final['pc'] - original['pc']) % 65536)
        value = final_value = 0
        if (0x80 <= opcode < 0xC0 and opcode % 8 == 6) or (opcode == 0xCB and second % 8 == 6):
            address = original['h']*256 + original['l']
            value = memory[address]
            final_value = dict(case['final']['ram'])[address]
            assert (final['h'],final['l']) == (initial['h'],initial['l'])
            initial.update(h=0xC0,l=0)
            final.update(h=0xC0,l=0)
        initial['m49152'] = value
        final.update(m49152=final_value, ticks=1, fault=0, halted=0)
        source = f'cb{second//64}' if opcode == 0xCB else 'sm83'
        result[source].append({'name':case['name'], 'opcode':opcode,
                              'byte':second,
                              'initial':initial, 'final':final})
    return result


def build(out):
    datasets = cases()
    for arithmetic, mode in [(True,'math'), (False,'native')]:
        root = out / mode
        root.mkdir(parents=True, exist_ok=True)
        css = machine(FixtureROM(), storage, arithmetic=arithmetic)
        css = css.replace('\n.machine {', '\n.pipeline-execute {')
        (root / 'machine.css').write_text(css)
        for source, vectors in datasets.items():
            for offset in range(0,len(vectors),CHUNK):
                html = ['<!doctype html><html><head><meta charset="utf-8">',
                        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'self\' \'unsafe-inline\'; script-src \'none\'">',
                        '<link rel="stylesheet" href="machine.css"><title>CPU conformance fixture</title></head><body>']
                for index, case in enumerate(vectors[offset:offset+CHUNK], offset):
                    seed = {**{f'next-{k}':v for k,v in case['initial'].items()},
                            'input-opcode':case['opcode'], 'input-byte':case['byte']}
                    inline = ''.join(f'--{k}:{v};' for k,v in seed.items())
                    html.append(f'<section style="{inline}"><div class="pipeline-read"><div class="pipeline-execute"><div class="pipeline-read result" data-index="{index}">case {index}</div></div></div></section>')
                html.append('</body></html>')
                (root / f'{source}-{offset//CHUNK}.html').write_text(''.join(html))
    return datasets


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expectations', action='store_true')
    if parser.parse_args().expectations:
        print(json.dumps(cases()))
    else:
        build(ROOT / 'dist/tests/conformance')
