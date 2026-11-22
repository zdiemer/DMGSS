#!/usr/bin/env python3
"""Generate static HTML/CSS. Never precompute runtime execution."""
from pathlib import Path
import shutil
import argparse
from cpu import machine, diagnostic, tile_rom, tile_css

ROOT = Path(__file__).resolve().parents[1]


def storage(states):
    """Two paused animation banks retain values between alternating clock phases."""
    declarations, current, latch, execute = [], [], [], []
    for name, (initial, expression) in states.items():
        declarations.append(f'@property --next-{name} {{ syntax: "<integer>"; inherits: true; initial-value: {initial}; }}')
        current.append(f'--{name}: var(--bank-{name}, {initial}); --next-{name}: {expression};')
        latch.append(f'--bank-{name}: var(--result-{name}, {initial});')
        execute.append(f'--result-{name}: var(--next-{name});')
    return '\n'.join(declarations) + '\n.machine {' + ''.join(current) + '}\n' + \
        '@keyframes latch {0%,100% {' + ''.join(latch) + '}}\n' + \
        '@keyframes execute {0%,100% {' + ''.join(execute) + '}}\n'


def build(rom=None, out=None, tile=False):
    out = out or ROOT / 'dist'
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    for file in (ROOT / 'src').iterdir():
        if file.is_file():
            shutil.copyfile(file, out / file.name)
    html = (out / 'index.html').read_text()
    html = html.replace('<!-- PIXELS -->', ''.join(f'<i class="pixel-{i}"></i>' for i in range(64)))
    if tile:
        html = html.replace('<body>', '<body class="tile-mode">')
    (out / 'index.html').write_text(html)
    (out / 'machine.css').write_text(machine(diagnostic() if rom is None else rom, storage) + tile_css())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', action='store_true')
    args = parser.parse_args()
    build()
    build(tile_rom(), ROOT / 'dist/tile', tile=True)
    if args.fixtures:
        import json
        for case in json.loads((ROOT / 'tests/cpu-cases.json').read_text()):
            build(case['rom'], ROOT / 'dist/tests' / case['name'])
