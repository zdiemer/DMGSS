#!/usr/bin/env python3
"""Generate static HTML/CSS. Never precompute runtime execution."""
from pathlib import Path
import shutil
import argparse
import re
from cpu import diagnostic, stack_rom, tile_rom
import portable
import checkpoint
import automatic
from alu import alu_rom
from bits import bits_rom
from high import high_rom, high_continuation, high_fill
from interrupts import interrupt_rom, interrupt_continuation
from timers import timer_rom
from serial_io import monitor_html
from serial_lab import serial_rom, boundary_rom as serial_boundary, boundary_seed as serial_seed
from rom import ROM

ROOT = Path(__file__).resolve().parents[1]


def current_cartridge(html, path):
    def mark(match):
        nav = match.group().replace(' aria-current="page"', '')
        return nav.replace(f'href="{path}"', f'aria-current="page" href="{path}"')
    return re.sub(r'<nav class="cartridges".*?</nav>', mark, html)


def build(rom=None, out=None, tile=False, bounded=False, stack=False, alu=False, bits=False, high=False, interrupts=False, timers=False, serial=False, initial=None, steps=portable.STEPS):
    out = out or ROOT / 'dist'
    if not bounded:
        cartridge = next((name for name,selected in [('serial',serial),('timers',timers),('interrupts',interrupts),('high',high),('bits',bits),('alu',alu),('stack',stack)] if selected), 'diagnostic')
        return build_automatic(diagnostic() if rom is None else rom, out, tile=tile, cartridge=cartridge, initial=initial, streaming=True)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    for file in (ROOT / 'src').iterdir():
        if file.is_file():
            shutil.copyfile(file, out / file.name)
    html = (out / 'index.html').read_text().replace('<!-- SERIAL MONITOR -->', monitor_html())
    html = html.replace('<!-- PIXELS -->', ''.join(f'<i class="pixel-{i}"></i>' for i in range(64)))
    html = html.replace('</aside>', '<p class="automatic-link"><a href="/automatic/">Try automatic continuation →</a></p></aside>')
    if tile:
        html = html.replace('<body>', '<body class="tile-mode">')
    if stack:
        html = html.replace('SYSTEM DIAGNOSTIC', 'STACK / NESTED CALLS')
    if alu:
        html = html.replace('SYSTEM DIAGNOSTIC', 'ALU / DECIMAL + FLAGS')
    if bits:
        html = html.replace('SYSTEM DIAGNOSTIC', 'BITS / ROTATE + SHIFT')
    if interrupts:
        html = html.replace('SYSTEM DIAGNOSTIC', 'INTERRUPTS / REQUEST + RETURN')
    if serial:
        html = html.replace('SYSTEM DIAGNOSTIC', 'SERIAL / SEND + RECEIVE')
        html = html.replace('<details class="serial-monitor">', '<details class="serial-monitor" open>')
        html = html.replace('</aside>', '<p class="serial-note">Serial lab sends OK, first waking HALT and then polling completion. A full byte needs 4,096 T-cycles, so this program needs multiple batches. <a href="/automatic/serial/">Use automatic mode</a> for the complete run; streaming is slow and compatible mode stops partway.</p></aside>')
    if timers:
        html = html.replace('SYSTEM DIAGNOSTIC', 'TIMER / OVERFLOW + WAKE')
    if high:
        html = html.replace('SYSTEM DIAGNOSTIC', 'HIGH RAM / RESTART + RETURN')
    program = diagnostic() if rom is None else rom
    if bounded:
        html = html.replace('<body', '<body data-engine="portable"')
        html = portable.wrap(html,steps=steps)
        html = html.replace('</head>', '<link rel="stylesheet" href="portable.css"></head>')
        html = html.replace('POWER ON', 'RUN').replace('POWER OFF', 'RESET VIEW').replace('class="start">POWER', 'class="start">RUN / RESET')
        html = html.replace('STREAMING MODE / TILE MEMORY', 'COMPATIBLE MODE / 128 STEPS')
        html = html.replace('href="/"', 'href="/portable/"').replace('href="/tile/"', 'href="/portable/tile/"').replace('href="/stack/"', 'href="/portable/stack/"').replace('href="/alu/"', 'href="/portable/alu/"').replace('href="/bits/"', 'href="/portable/bits/"').replace('href="/high/"', 'href="/portable/high/"').replace('href="/interrupts/"', 'href="/portable/interrupts/"').replace('href="/timers/"', 'href="/portable/timers/"').replace('href="/serial/"', 'href="/portable/serial/"')
        html = html.replace('<a href="/portable/">Switch to compatible mode</a>', '<a href="/">Switch to streaming mode</a>')
        html = html.replace('>RUNNING<', '>STEP LIMIT<').replace('CPU WRITING VRAM', '128-STEP LIMIT')
        html = html.replace('Testing CSS state storage…', 'Evaluating CSS stages…')
        html = html.replace('READY WHEN YOU ARE', 'UP TO 128 INSTRUCTIONS')
        html = html.replace('The clock and state live in your browser’s stylesheet engine. No JavaScript. No hidden emulator.', 'Your browser executes the ROM through 128 CSS stages. No JavaScript. No execution trace generated ahead of time.')
        html = re.sub(r'<div class="compat-warning">.*?</div>', '<div class="compat-warning"><strong>Bounded execution: 128 instructions.</strong> Run evaluates the cartridge in CSS. Quiescent HALT and faults stop it early; timer waits also consume the batch budget. A loop reaches the step limit; this mode cannot run games indefinitely. Tested in WebKit and reported working in iOS Chrome.</div>', html)
        html = re.sub(r'<div class="unsupported-screen">.*?</div>', '<div class="unsupported-screen"><strong>CSS SUPPORT NEEDED</strong><span>Please update your browser.</span><span>This mode needs CSS math and style queries.</span></div>', html)
        html = html.replace('INSTRUCTIONS EXECUTED', 'INSTRUCTIONS / MAX 128')
        html = html.replace('</aside>', '<p class="checkpoint-link"><a href="/checkpoint/">Try manual checkpoints →</a></p></aside>')
        html = html.replace('Reset reloads the machine. Nothing is saved.', 'Reset view clears the run. Cartridge state is not saved.')
        (out / 'machine.css').write_text(portable.stylesheet(program, initial=initial))
    active = ('/portable' if bounded else '') + ('/serial/' if serial else '/timers/' if timers else '/interrupts/' if interrupts else '/high/' if high else '/bits/' if bits else '/alu/' if alu else '/stack/' if stack else '/tile/' if tile else '/')
    (out / 'index.html').write_text(current_cartridge(html, active))


def build_checkpoint(rom, out, tile=False, cartridge="counter", initial=None):
    build(rom, out, tile=tile, bounded=True, stack=cartridge == 'stack', alu=cartridge == 'alu', bits=cartridge == 'bits', high=cartridge == 'high', interrupts=cartridge == 'interrupts', timers=cartridge == 'timers', serial=cartridge == 'serial')
    css, commit, inputs, controls, readers, input_css, copy_css = checkpoint.generate(rom, initial=initial)
    (out / 'machine.css').write_text(css)
    # Keep each stylesheet below Chromium's per-sheet selector budget.
    (out / 'checkpoint-inputs.css').write_text(input_css)
    (out / 'checkpoint-copy.css').write_text(copy_css)
    html = (out / 'index.html').read_text()
    html = html.replace('<body ', '<body data-checkpoint ')
    html = re.sub(r'<p class="checkpoint-link">.*?</p>', '', html)
    html = html.replace('</head>', '<link rel="stylesheet" href="checkpoint.css"><link rel="stylesheet" href="checkpoint-inputs.css"><link rel="stylesheet" href="checkpoint-copy.css"></head>')
    html = html.replace('<div class="clock">', commit + '<div class="clock">' + inputs)
    html = html.replace('</div></div>\n    </section>', '</div>' * readers + '</div></div>\n    </section>')
    html = html.replace('<div class="brand">', controls + '<div class="brand">')
    html = html.replace('COMPATIBLE MODE / 128 STEPS', 'MANUAL CHECKPOINTS / 128 STEPS')
    html = html.replace('RESET VIEW', 'PAUSE').replace('RUN / RESET', 'RUN / PAUSE')
    html = html.replace('>STEP LIMIT<', '>BATCH COMPLETE<').replace('INSTRUCTIONS / MAX 128', 'TOTAL INSTRUCTIONS')
    html = html.replace('href="/portable/">CPU check', 'href="/checkpoint/">Counter</a><a href="/checkpoint/diagnostic/">CPU check')
    html = html.replace('href="/portable/tile/"', 'href="/checkpoint/tile/"')
    html = html.replace('href="/portable/stack/"', 'href="/checkpoint/stack/"')
    html = html.replace('href="/portable/alu/"', 'href="/checkpoint/alu/"')
    html = html.replace('href="/portable/bits/"', 'href="/checkpoint/bits/"')
    html = html.replace('href="/portable/high/"', 'href="/checkpoint/high/"')
    html = html.replace('href="/portable/interrupts/"', 'href="/checkpoint/interrupts/"')
    html = html.replace('href="/portable/timers/"', 'href="/checkpoint/timers/"')
    html = html.replace('href="/portable/serial/"', 'href="/checkpoint/serial/"')
    active = '/checkpoint/serial/' if cartridge == 'serial' else '/checkpoint/timers/' if cartridge == 'timers' else '/checkpoint/interrupts/' if cartridge == 'interrupts' else '/checkpoint/high/' if cartridge == 'high' else '/checkpoint/bits/' if cartridge == 'bits' else '/checkpoint/alu/' if cartridge == 'alu' else '/checkpoint/stack/' if cartridge == 'stack' else '/checkpoint/tile/' if tile else '/checkpoint/diagnostic/' if cartridge == 'diagnostic' else '/checkpoint/'
    html = current_cartridge(html, active)
    if cartridge == 'counter' and not tile:
        html = html.replace('SYSTEM DIAGNOSTIC', 'RAM C000: <span class="checkpoint-memory"></span>')
    html = html.replace('<a href="/">Switch to streaming mode</a>', '<a href="/portable/">Back to compatible mode</a>')
    html = html.replace('<div><dt>F</dt>', '<div><dt>RAM C000</dt><dd class="checkpoint-memory"></dd></div><div><dt>F</dt>')
    html = re.sub(r'<div class="compat-warning">.*?</div>', '<div class="compat-warning"><strong>Manual checkpoint experiment.</strong> Each run executes up to 128 instructions. Save each changed bit, then tap Run next 128 to continue from that state. Timer waits also consume batch steps. Several taps may be needed; there is no automatic copying. Pause keeps stored banks; Reset clears everything. The total counter wraps at 65,536. This new mode still needs iOS verification.</div>', html)
    html = html.replace('Reset view clears the run. Cartridge state is not saved.', 'State lives in native checkbox controls. Reset clears the banks; there is no save-file persistence.')
    html = html.replace('Embedded diagnostic: loads, arithmetic, branches and RAM.', 'Counter cartridge: repeatedly increments RAM C000, wrapping at 255. CPU check runs the original diagnostic.')
    (out / 'index.html').write_text(html)


def build_automatic(rom, out, tile=False, cartridge="counter", initial=None, streaming=False):
    build(rom, out, tile=tile, bounded=True, stack=cartridge == 'stack', alu=cartridge == 'alu', bits=cartridge == 'bits', high=cartridge == 'high', interrupts=cartridge == 'interrupts', timers=cartridge == 'timers', serial=cartridge == 'serial', steps=1 if streaming else portable.STEPS)
    # Keep the shared shell's streaming-mode visibility/clock rules below this
    # mode's rules, including when its capability gate fails.
    shell = (out / 'style.css').read_text()
    (out / 'style.css').write_text('@layer console {\n' + shell + '\n}\n')
    css, cells, readers = automatic.generate(rom, initial=initial, arithmetic=not streaming)
    (out / 'machine.css').write_text(css)
    html = (out / 'index.html').read_text()
    opening = ''.join(f'<div class="auto-reader auto-reader-{i}">' for i in range(readers)) + '<div class="auto-seed">'
    html = html.replace('<div class="clock">', '<div class="clock">' + opening)
    html = html.replace('</div></div>\n    </section>', '</div>' * (readers + 1) + '</div></div>\n    </section>')
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
    html = html.replace('href="/portable/stack/"', 'href="/automatic/stack/"')
    html = html.replace('href="/portable/alu/"', 'href="/automatic/alu/"')
    html = html.replace('href="/portable/bits/"', 'href="/automatic/bits/"')
    html = html.replace('href="/portable/high/"', 'href="/automatic/high/"')
    html = html.replace('href="/portable/interrupts/"', 'href="/automatic/interrupts/"')
    html = html.replace('href="/portable/timers/"', 'href="/automatic/timers/"')
    html = html.replace('href="/portable/serial/"', 'href="/automatic/serial/"')
    active = '/automatic/serial/' if cartridge == 'serial' else '/automatic/timers/' if cartridge == 'timers' else '/automatic/interrupts/' if cartridge == 'interrupts' else '/automatic/high/' if cartridge == 'high' else '/automatic/bits/' if cartridge == 'bits' else '/automatic/alu/' if cartridge == 'alu' else '/automatic/stack/' if cartridge == 'stack' else '/automatic/tile/' if tile else '/automatic/diagnostic/' if cartridge == 'diagnostic' else '/automatic/'
    html = current_cartridge(html, active)
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
    if streaming:
        html = html.replace('data-engine="automatic"', 'data-engine="streaming"')
        html = html.replace('<a href="/automatic/">Counter</a>', '')
        html = html.replace('/automatic/diagnostic/', '/').replace('/automatic/', '/')
        html = html.replace('AUTOMATIC CONTINUATION / EXPERIMENTAL', 'STREAMING / ONE INSTRUCTION AT A TIME')
        html = html.replace('next batch', 'next instruction').replace('Testing automatic storage…', 'Testing streaming storage…')
        html = html.replace('Counter cartridge repeatedly increments RAM C000. CPU check tests arithmetic, branches and RAM.', 'CPU check tests arithmetic, branches and RAM.')
        html = re.sub(r'<div class="compat-warning">.*?</div>', '<div class="compat-warning"><strong>Streaming experiment.</strong> Each CSS step commits one instruction through scroll storage. This mode needs CSS conditionals and scroll timelines. Chrome on iOS uses WebKit; feature support and device memory determine whether it works. Try <a href="/portable/">Compatible mode</a> if it cannot start. No full-speed or game compatibility claim.</div>', html)
        html = html.replace('This mode needs CSS scroll timelines.', 'This mode needs CSS conditionals and scroll timelines.')
        shell = (out / 'style.css').read_text()
        shell += '\nbody[data-automatic][data-engine="streaming"] {--automatic-style:0;}\n@supports (width:if(style(--x:1):1px;else:2px)) {body[data-automatic][data-engine="streaming"] {--automatic-style:1;}}\n'
        (out / 'style.css').write_text(shell)
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
    build(stack_rom(), ROOT / 'dist/stack', stack=True)
    build(stack_rom(), ROOT / 'dist/portable/stack', bounded=True, stack=True)
    build_checkpoint(stack_rom(), ROOT / 'dist/checkpoint/stack', cartridge='stack')
    build_automatic(stack_rom(), ROOT / 'dist/automatic/stack', cartridge='stack')
    build(alu_rom(), ROOT / 'dist/alu', alu=True)
    build(alu_rom(), ROOT / 'dist/portable/alu', bounded=True, alu=True)
    build_checkpoint(alu_rom(), ROOT / 'dist/checkpoint/alu', cartridge='alu')
    build_automatic(alu_rom(), ROOT / 'dist/automatic/alu', cartridge='alu')
    build(bits_rom(), ROOT / 'dist/bits', bits=True)
    build(bits_rom(), ROOT / 'dist/portable/bits', bounded=True, bits=True)
    build_checkpoint(bits_rom(), ROOT / 'dist/checkpoint/bits', cartridge='bits')
    build_automatic(bits_rom(), ROOT / 'dist/automatic/bits', cartridge='bits')
    build(high_rom(), ROOT / 'dist/high', high=True)
    build(high_rom(), ROOT / 'dist/portable/high', bounded=True, high=True)
    build_checkpoint(high_rom(), ROOT / 'dist/checkpoint/high', cartridge='high')
    build_automatic(high_rom(), ROOT / 'dist/automatic/high', cartridge='high')
    build(interrupt_rom(), ROOT / 'dist/interrupts', interrupts=True)
    build(interrupt_rom(), ROOT / 'dist/portable/interrupts', bounded=True, interrupts=True)
    build_checkpoint(interrupt_rom(), ROOT / 'dist/checkpoint/interrupts', cartridge='interrupts')
    build_automatic(interrupt_rom(), ROOT / 'dist/automatic/interrupts', cartridge='interrupts')
    build(timer_rom(), ROOT / 'dist/timers', timers=True)
    build(timer_rom(), ROOT / 'dist/portable/timers', bounded=True, timers=True)
    build_checkpoint(timer_rom(), ROOT / 'dist/checkpoint/timers', cartridge='timers')
    build_automatic(timer_rom(), ROOT / 'dist/automatic/timers', cartridge='timers')
    build(serial_rom(), ROOT / 'dist/serial', serial=True)
    build(serial_rom(), ROOT / 'dist/portable/serial', bounded=True, serial=True)
    build_checkpoint(serial_rom(), ROOT / 'dist/checkpoint/serial', cartridge='serial')
    build_automatic(serial_rom(), ROOT / 'dist/automatic/serial', cartridge='serial')
    if args.fixtures:
        import work_ram_fixtures
        work_ram_fixtures.build(build_automatic, ROOT / "dist/automatic/tests/full-ram")
        import packing_fixtures
        packing_fixtures.build(build_automatic, ROOT / 'dist/automatic/tests/packing')
        import rom_fixtures
        rom_fixtures.build(ROOT / 'dist/tests/rom-lookup')
        build_automatic(serial_boundary(), ROOT / 'dist/automatic/tests/serial-boundary', initial=serial_seed())
        build_checkpoint(serial_boundary(), ROOT / 'dist/checkpoint/tests/serial-boundary', initial=serial_seed())
        midbit=serial_seed() | {'serial-phase':128,'serial-bits':6,'serial-tx':16,'m65281':127}
        build_checkpoint(serial_boundary(), ROOT / 'dist/checkpoint/tests/serial-midbit', initial=midbit)
        near=serial_seed() | {'serial-phase':508}
        build(serial_boundary(), ROOT / 'dist/tests/serial-boundary', initial=near)
        build(serial_boundary(), ROOT / 'dist/portable/tests/serial-boundary', bounded=True, initial=near)
        build_automatic(ROM([0x76]), ROOT / 'dist/automatic/tests/serial-idle', initial={'halted':1,'m65281':65,'m65282':255})
        build_automatic(ROM([0x76]), ROOT / 'dist/automatic/tests/serial-external', initial={'m65281':65,'m65282':254})

        import timer_fixtures
        for case in timer_fixtures.cases():
            build_automatic(ROM(case['rom']), ROOT / f'dist/automatic/tests/mooneye-{case["name"]}')
        boundary=bytearray(0x100)
        boundary[0x50:0x55]=bytes([0xAF,0xE0,7,0x04,0xD9])
        boundary.extend([0]*127+[0x76,0x3E,0xA5,0xEA,2,0xC0,0x76])
        seed={'sp':65534,'ime':1,'m65535':4,'m65285':224,'m65286':42,'m65287':253}
        build_checkpoint(ROM(boundary,base=0), ROOT / 'dist/checkpoint/tests/timer-boundary', initial=seed)
        build_automatic(ROM(boundary,base=0), ROOT / 'dist/automatic/tests/timer-boundary', initial=seed)
        build_automatic(ROM([0x76]), ROOT / 'dist/automatic/tests/timer-idle', initial={'halted':1,'m65287':252})
        for kind in ('delay','service','bug'):
            build_checkpoint(interrupt_continuation(kind), ROOT / f'dist/checkpoint/tests/interrupt-{kind}')
            build_automatic(interrupt_continuation(kind), ROOT / f'dist/automatic/tests/interrupt-{kind}')

        import json
        cases = json.loads((ROOT / 'tests/cpu-cases.json').read_text()) + json.loads((ROOT / 'tests/addressing-cases.json').read_text()) + json.loads((ROOT / 'tests/stack-cases.json').read_text()) + json.loads((ROOT / 'tests/alu-cases.json').read_text()) + json.loads((ROOT / 'tests/cb-cases.json').read_text()) + json.loads((ROOT / 'tests/high-cases.json').read_text()) + json.loads((ROOT / 'tests/interrupt-cases.json').read_text())
        for case in cases:
            program = ROM(case['rom'], base=case['base'], compact=False) if 'base' in case else case['rom']
            build(program, ROOT / 'dist/tests' / case['name'], initial=case.get('initial'))
            build(program, ROOT / 'dist/portable/tests' / case['name'], bounded=True, initial=case.get('initial'))
        # 128th step is BIT [HL]; the next batch modifies memory and branches.
        # Seed near wrap to check that all modes retain a full 16-bit cycle count.
        timing = [0x21,0,0xC0] + [0]*126 + [0xCB,0x46,0x36,0x81,0xCB,0x06,0x20,0,0x76]
        build_checkpoint(timing, ROOT / 'dist/checkpoint/tests/timing', initial={'tcycles':65520})
        build_automatic(timing, ROOT / 'dist/automatic/tests/timing', initial={'tcycles':65520})
        wake = next(case for case in cases if case['name'] == 'interrupt-halt-wakes-with-ime')
        build_automatic(ROM(wake['rom'],base=0), ROOT / 'dist/automatic/tests/interrupt-wake', initial=wake['initial'])
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

        # The inner RET is instruction 128. Outer still has saved BC and its
        # return address in RAM, so POP/RET must consume a transferred bank.
        stack_continuation = [0x31,0x40,0xC0,0x01,0x34,0x12,0xCD,0x0A,1,0x76,0xC5,0xCD,0x11,1,0xC1,0xC9,0xD3] + [0] * 121 + [0x01,0xCD,0xAB,0xC9]
        build_checkpoint(stack_continuation, ROOT / 'dist/checkpoint/tests/stack-continuation')
        build_automatic(stack_continuation, ROOT / 'dist/automatic/tests/stack-continuation')
        build_automatic([0x31,1,0xC0,0x01,0x34,0x12,0xC5], ROOT / 'dist/automatic/tests/stack-trap')

        carry_continuation = [0x3E,255,0x37] + [0] * 126 + [0xCE,0,0xEA,2,0xC0,0x76]
        cb_continuation = [0x21,0,0xC0,0x36,0x81,0x37] + [0]*124 + [0xCB,0x1E,0xCB,0x7E,0x76]
        build_checkpoint(cb_continuation, ROOT / 'dist/checkpoint/tests/cb-carry')
        build_automatic(cb_continuation, ROOT / 'dist/automatic/tests/cb-carry')
        build_checkpoint(carry_continuation, ROOT / 'dist/checkpoint/tests/alu-carry')
        build_automatic(carry_continuation, ROOT / 'dist/automatic/tests/alu-carry')
        build_checkpoint(high_continuation(), ROOT / 'dist/checkpoint/tests/high-continuation')
        build_automatic(high_continuation(), ROOT / 'dist/automatic/tests/high-continuation')
        build(high_fill(), ROOT / 'dist/portable/tests/high-fill', bounded=True)
        build_automatic(high_fill(), ROOT / 'dist/automatic/tests/high-fill')
        import conformance
        conformance.build(ROOT / "dist/tests/conformance")
