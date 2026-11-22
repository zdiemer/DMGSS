#!/usr/bin/env python3
"""Generate static HTML/CSS. Never precompute runtime execution."""
from pathlib import Path
import shutil
import argparse
import re
from cpu import machine, diagnostic, tile_rom, tile_css
import portable

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


def build(rom=None, out=None, tile=False, bounded=False):
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
    program = diagnostic() if rom is None else rom
    if bounded:
        html = html.replace('<body', '<body data-engine="portable"')
        html = portable.wrap(html)
        html = html.replace('</head>', '<link rel="stylesheet" href="portable.css"></head>')
        html = html.replace('POWER ON', 'RUN').replace('POWER OFF', 'RESET VIEW').replace('class="start">POWER', 'class="start">RUN / RESET')
        html = html.replace('STREAMING MODE / TILE MEMORY', 'COMPATIBLE MODE / 128 STEPS')
        html = html.replace('href="/"', 'href="/portable/"').replace('href="/tile/"', 'href="/portable/tile/"')
        html = html.replace('<a href="/portable/">Switch to compatible mode</a>', '<a href="/">Switch to streaming mode</a>')
        html = html.replace('>RUNNING<', '>STEP LIMIT<').replace('CPU WRITING VRAM', '128-STEP LIMIT')
        html = html.replace('Testing CSS state storage…', 'Evaluating CSS stages…')
        html = html.replace('READY WHEN YOU ARE', '128 INSTRUCTIONS PER RUN')
        html = html.replace('The clock and state live in your browser’s stylesheet engine. No JavaScript. No hidden emulator.', 'Your browser executes the ROM through 128 CSS stages. No JavaScript. No execution trace generated ahead of time.')
        html = re.sub(r'<div class="compat-warning">.*?</div>', '<div class="compat-warning"><strong>Bounded execution: 128 instructions.</strong> Run evaluates the cartridge in CSS. Halt and faults stop it early. A loop reaches the step limit; this mode cannot run games indefinitely. Tested in WebKit; real-device iOS validation is still needed.</div>', html)
        html = re.sub(r'<div class="unsupported-screen">.*?</div>', '<div class="unsupported-screen"><strong>CSS SUPPORT NEEDED</strong><span>Please update your browser.</span><span>This mode needs CSS math and style queries.</span></div>', html)
        html = html.replace('INSTRUCTIONS EXECUTED', 'INSTRUCTIONS / MAX 128')
        html = html.replace('Reset reloads the machine. Nothing is saved.', 'Reset view clears the run. Cartridge state is not saved.')
        (out / 'machine.css').write_text(portable.stylesheet(program))
    else:
        (out / 'machine.css').write_text(machine(program, storage) + tile_css())
    (out / 'index.html').write_text(html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', action='store_true')
    args = parser.parse_args()
    build()
    build(tile_rom(), ROOT / 'dist/tile', tile=True)
    build(out=ROOT / 'dist/portable', bounded=True)
    build(tile_rom(), ROOT / 'dist/portable/tile', tile=True, bounded=True)
    if args.fixtures:
        import json
        for case in json.loads((ROOT / 'tests/cpu-cases.json').read_text()):
            build(case['rom'], ROOT / 'dist/tests' / case['name'])
            build(case['rom'], ROOT / 'dist/portable/tests' / case['name'], bounded=True)
        build([0x18, 0xFE], ROOT / 'dist/portable/tests/loop', bounded=True)
        build([0xD3], ROOT / 'dist/portable/tests/tile-fault', tile=True, bounded=True)
