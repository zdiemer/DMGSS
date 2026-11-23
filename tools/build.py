#!/usr/bin/env python3
"""Generate static HTML/CSS. Never precompute runtime execution."""
from pathlib import Path
import shutil
import argparse
import re
from cpu import machine, diagnostic, tile_rom, tile_css
import portable
import checkpoint
import automatic

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
    html = html.replace('</aside>', '<p class="automatic-link"><a href="/automatic/">Try automatic continuation →</a></p></aside>')
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
        html = re.sub(r'<div class="compat-warning">.*?</div>', '<div class="compat-warning"><strong>Bounded execution: 128 instructions.</strong> Run evaluates the cartridge in CSS. Halt and faults stop it early. A loop reaches the step limit; this mode cannot run games indefinitely. Tested in WebKit and reported working in iOS Chrome.</div>', html)
        html = re.sub(r'<div class="unsupported-screen">.*?</div>', '<div class="unsupported-screen"><strong>CSS SUPPORT NEEDED</strong><span>Please update your browser.</span><span>This mode needs CSS math and style queries.</span></div>', html)
        html = html.replace('INSTRUCTIONS EXECUTED', 'INSTRUCTIONS / MAX 128')
        html = html.replace('</aside>', '<p class="checkpoint-link"><a href="/checkpoint/">Try manual checkpoints →</a></p></aside>')
        html = html.replace('Reset reloads the machine. Nothing is saved.', 'Reset view clears the run. Cartridge state is not saved.')
        (out / 'machine.css').write_text(portable.stylesheet(program))
    else:
        (out / 'machine.css').write_text(machine(program, storage) + tile_css())
    (out / 'index.html').write_text(html)


def build_checkpoint(rom, out, tile=False, cartridge="counter", initial=None):
    build(rom, out, tile=tile, bounded=True)
    css, inputs, controls = checkpoint.generate(rom, initial=initial)
    (out / 'machine.css').write_text(css)
    html = (out / 'index.html').read_text()
    html = html.replace('<body ', '<body data-checkpoint ')
    html = re.sub(r'<p class="checkpoint-link">.*?</p>', '', html)
    html = html.replace('</head>', '<link rel="stylesheet" href="checkpoint.css"></head>')
    html = html.replace('<div class="clock">', inputs + '<div class="clock">')
    html = html.replace('<div class="brand">', controls + '<div class="brand">')
    html = html.replace('COMPATIBLE MODE / 128 STEPS', 'MANUAL CHECKPOINTS / 128 STEPS')
    html = html.replace('RESET VIEW', 'PAUSE').replace('RUN / RESET', 'RUN / PAUSE')
    html = html.replace('>STEP LIMIT<', '>BATCH COMPLETE<').replace('INSTRUCTIONS / MAX 128', 'TOTAL INSTRUCTIONS')
    html = html.replace('href="/portable/">CPU check', 'href="/checkpoint/">Counter</a><a href="/checkpoint/diagnostic/">CPU check')
    html = html.replace('href="/portable/tile/"', 'href="/checkpoint/tile/"')
    active = '/checkpoint/tile/' if tile else '/checkpoint/diagnostic/' if cartridge == 'diagnostic' else '/checkpoint/'
    html = html.replace(f'href="{active}"', f'aria-current="page" href="{active}"')
    if cartridge == 'counter' and not tile:
        html = html.replace('SYSTEM DIAGNOSTIC', 'RAM C000: <span class="checkpoint-memory"></span>')
    html = html.replace('<a href="/">Switch to streaming mode</a>', '<a href="/portable/">Back to compatible mode</a>')
    html = html.replace('<div><dt>F</dt>', '<div><dt>RAM C000</dt><dd class="checkpoint-memory"></dd></div><div><dt>F</dt>')
    html = re.sub(r'<div class="compat-warning">.*?</div>', '<div class="compat-warning"><strong>Manual checkpoint experiment.</strong> Each run executes up to 128 instructions. Save each changed bit, then tap Run next 128 to continue from that state. Several taps may be needed; there is no automatic copying. Pause keeps stored banks; Reset clears everything. The total counter wraps at 65,536. This new mode still needs iOS verification.</div>', html)
    html = html.replace('Reset view clears the run. Cartridge state is not saved.', 'State lives in native checkbox controls. Reset clears the banks; there is no save-file persistence.')
    html = html.replace('Embedded diagnostic: loads, arithmetic, branches and RAM.', 'Counter cartridge: repeatedly increments RAM C000, wrapping at 255. CPU check runs the original diagnostic.')
    (out / 'index.html').write_text(html)


def build_automatic(rom, out, tile=False, cartridge="counter", initial=None):
    build(rom, out, tile=tile, bounded=True)
    # Keep the shared shell's streaming-mode visibility/clock rules below this
    # mode's rules, including when its capability gate fails.
    shell = (out / 'style.css').read_text()
    (out / 'style.css').write_text('@layer console {\n' + shell + '\n}\n')
    css, cells = automatic.generate(rom, initial=initial)
    (out / 'machine.css').write_text(css)
    html = (out / 'index.html').read_text()
    html = html.replace('data-engine="portable"', 'data-engine="automatic" data-automatic')
    html = html.replace('href="portable.css"', 'href="automatic.css"')
    html = re.sub(r'<p class="(?:checkpoint|automatic)-link">.*?</p>', '', html)
    html = html.replace('<div class="pipeline-read machine">', '<div class="pipeline-read auto-output">' + cells + '<div class="machine">')
    html = html.replace('</details>\n      </div>', '</details>\n      </div></div>')
    html = html.replace('COMPATIBLE MODE / 128 STEPS', 'AUTOMATIC CONTINUATION / EXPERIMENTAL')
    html = html.replace('RESET VIEW', 'PAUSE').replace('RUN / RESET', 'RUN / PAUSE')
    html = html.replace('>STEP LIMIT<', '>RUNNING<').replace('128-STEP LIMIT', 'CPU WRITING VRAM')
    html = html.replace('INSTRUCTIONS / MAX 128', 'TOTAL INSTRUCTIONS')
    html = html.replace('<strong class="running-message">RUNNING</strong>', '<strong class="running-message"><span class="auto-running">RUNNING</span><span class="auto-paused">PAUSED</span></strong>')
    html = html.replace('href="/portable/">CPU check', 'href="/automatic/">Counter</a><a href="/automatic/diagnostic/">CPU check')
    html = html.replace('href="/portable/tile/"', 'href="/automatic/tile/"')
    active = '/automatic/tile/' if tile else '/automatic/diagnostic/' if cartridge == 'diagnostic' else '/automatic/'
    html = html.replace(f'href="{active}"', f'aria-current="page" href="{active}"')
    if cartridge == 'counter' and not tile:
        html = html.replace('SYSTEM DIAGNOSTIC', 'RAM C000: <span class="automatic-memory"></span>')
    html = html.replace('<a href="/">Switch to streaming mode</a>', '<a href="/portable/">Back to compatible mode</a>')
    html = html.replace('<div><dt>F</dt>', '<div><dt>RAM C000</dt><dd class="automatic-memory"></dd></div><div><dt>F</dt>')
    html = html.replace('Your browser executes the ROM through 128 CSS stages. No JavaScript. No execution trace generated ahead of time.', 'Press Run once. CSS executes the ROM and automatically carries its state into the next batch. Pause keeps your place; Reset starts over.')
    html = re.sub(r'<div class="compat-warning">.*?</div>', '<div class="compat-warning"><strong>Automatic continuation experiment.</strong> Tested in Chromium and Linux WebKit with scroll timelines. The counter is user-confirmed on iOS Chrome; other features still need device checks. If it cannot advance, try <a href="/checkpoint/">manual checkpoints</a> or <a href="/portable/">compatible mode</a>. The instruction counter wraps at 65,536; this is not a full-speed or game-ready emulator.</div>', html)
    html = re.sub(r'<div class="unsupported-screen">.*?</div>', '<div class="unsupported-screen"><strong>BROWSER LIMIT</strong><span>This mode needs CSS scroll timelines.</span><a class="portable-link" href="/checkpoint/">Try manual checkpoints</a></div>', html)
    html = html.replace('Evaluating CSS stages…', 'Testing automatic storage…')
    html = html.replace('Reset view clears the run. Cartridge state is not saved.', 'State lasts until reset or navigation. No persistent saves yet.')
    html = html.replace('Embedded diagnostic: loads, arithmetic, branches and RAM.', 'Counter cartridge repeatedly increments RAM C000. CPU check tests arithmetic, branches and RAM.')
    (out / 'index.html').write_text(html)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures', action='store_true')
    args = parser.parse_args()
    build()
    build(tile_rom(), ROOT / 'dist/tile', tile=True)
    build(out=ROOT / 'dist/portable', bounded=True)
    build(tile_rom(), ROOT / 'dist/portable/tile', tile=True, bounded=True)
    build_checkpoint(checkpoint.counter_rom(), ROOT / 'dist/checkpoint')
    build_checkpoint(diagnostic(), ROOT / 'dist/checkpoint/diagnostic', cartridge='diagnostic')
    build_checkpoint(tile_rom(), ROOT / 'dist/checkpoint/tile', tile=True)
    build_automatic(checkpoint.counter_rom(), ROOT / 'dist/automatic')
    build_automatic(diagnostic(), ROOT / 'dist/automatic/diagnostic', cartridge='diagnostic')
    build_automatic(tile_rom(), ROOT / 'dist/automatic/tile', tile=True)
    if args.fixtures:
        import json
        cases = json.loads((ROOT / 'tests/cpu-cases.json').read_text()) + json.loads((ROOT / 'tests/addressing-cases.json').read_text())
        for case in cases:
            build(case['rom'], ROOT / 'dist/tests' / case['name'])
            build(case['rom'], ROOT / 'dist/portable/tests' / case['name'], bounded=True)
        build([0x18, 0xFE], ROOT / 'dist/portable/tests/loop', bounded=True)
        build([0xD3], ROOT / 'dist/portable/tests/tile-fault', tile=True, bounded=True)

        build_checkpoint([0x06,100,0x3E,0,0x3C,0x05,0x20,0xFC,0xEA,0,0xC0,0x76], ROOT / 'dist/checkpoint/tests/long-loop')
        build_checkpoint([0xD3], ROOT / 'dist/checkpoint/tests/trap')
        retained = [0x3E,0xAA,0xEA,0x0F,0x80]
        for opcode, value in zip([0x06,0x0E,0x16,0x1E,0x26,0x2E], [1,2,4,8,16,32]):
            retained.extend([opcode,value])
        retained.extend([0x00] * 120)  # First batch ends after these NOPs.
        retained.extend([0xAF,0xFA,0x0F,0x80,0xEA,0x3F,0xC0,0x76])
        build_checkpoint(retained, ROOT / 'dist/checkpoint/tests/register-vram')
        build_checkpoint(checkpoint.counter_rom(), ROOT / 'dist/checkpoint/tests/tick-wrap', initial={'ticks':65472})
        build_automatic([0x06,100,0x3E,0,0x3C,0x05,0x20,0xFC,0xEA,0,0xC0,0x76], ROOT / 'dist/automatic/tests/long-loop')
        build_automatic([0xD3], ROOT / 'dist/automatic/tests/trap')
        build_automatic(retained, ROOT / 'dist/automatic/tests/register-vram')
        build_automatic(checkpoint.counter_rom(), ROOT / 'dist/automatic/tests/tick-wrap', initial={'ticks':65472})
        # Runtime loop fills RAM through HL, then reads backwards into VRAM via
        # DE. 344 instructions cross two bank swaps; SP must retain all 16 bits.
        addressing = [0x31,0xDC,0xFE,0x21,0,0xC0,0x06,64,0x3E,0,
                      0x22,0x3C,0x05,0x20,0xFB,
                      0x21,0x3F,0xC0,0x11,0,0x80,0x06,16,
                      0x3A,0x12,0x13,0x05,0x20,0xFA,0x76]
        build_automatic(addressing, ROOT / 'dist/automatic/tests/addressing-loop')
        # A short checkpoint fixture keeps bit copying practical while testing
        # that a word-sized SP survives a real bank transfer.
        pointer_checkpoint = [0x31,0xDC,0xFE,0x21,0,0xC0] + [0] * 126 + [0x36,42,0x2A,0x76]
        build_checkpoint(pointer_checkpoint, ROOT / 'dist/checkpoint/tests/addressing')
        build_automatic([0x21,0,1,0x3E,7,0x22], ROOT / 'dist/automatic/tests/addressing-trap')
