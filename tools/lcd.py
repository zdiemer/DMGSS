"""Emit a fixed-duration LCD timing circuit; no pixel renderer or ROM execution.

Six M-cycle samples share the timer's accepted CPU/HALT clock. Mode 3 has its
minimum 172-dot duration. Startup, STAT write glitches and sub-M-cycle races
remain explicit approximations; this is not a cycle-accurate PPU.
"""
LCDC, STAT, LY, LYC = 0xFF40, 0xFF41, 0xFF44, 0xFF45
REGISTERS = (LCDC, STAT, LY, LYC)


def circuit(equals):
    expr = {
        'lcd-live': f'calc(round(down,var(--m{LCDC}) / 128))',
        'lcd-step': 'calc(min(1,var(--timer-cycles)))',
        'lcd-line0': 'var(--lcd-line)', 'lcd-dot0': 'var(--lcd-dot)',
        'lcd-signal0': 'var(--lcd-stat)', 'lcd-request0': '0',
        'lcd-vblank0': '0',
        'lcd-control': f'calc(mod(round(down,var(--m{STAT}) / 8),16) * 8)',
    }

    def sample(suffix, live, control, compare):
        line, dot = f'lcd-line{suffix}', f'lcd-dot{suffix}'
        # LY returns to zero one M-cycle into the last VBlank line. The internal
        # line stays 153, so neither mode 2 nor a new frame starts prematurely.
        expr[f'lcd-ly{suffix}'] = f'calc(var(--{line}) * (1 - ({equals(line,153)}) * min(1,var(--{dot}) / 4)))'
        expr[f'lcd-blank{suffix}'] = f'calc(max(0,min(1,var(--{line}) - 143)))'
        expr[f'lcd-mode{suffix}'] = f'calc(({live}) * (var(--lcd-blank{suffix}) + (1 - var(--lcd-blank{suffix})) * (2 * max(0,min(1,80 - var(--{dot}))) + 3 * max(0,min(1,var(--{dot}) - 79,252 - var(--{dot}))))))'
        expr[f'lcd-match{suffix}'] = f'calc(max(0,1 - abs(var(--lcd-ly{suffix}) - ({compare}))))'
        sources = [f'mod(round(down,({control}) / {1 << (3+mode)}),2) * ({equals(f"lcd-mode{suffix}",mode)})' for mode in range(3)]
        sources.append(f'mod(round(down,({control}) / 64),2) * var(--lcd-match{suffix})')
        expr[f'lcd-signal{suffix}'] = f'calc(({live}) * max(' + ','.join(sources) + '))'
        expr[f'lcd-status{suffix}'] = f'calc(128 + ({control}) + 4 * var(--lcd-match{suffix}) + var(--lcd-mode{suffix}))'

    for i in range(1,7):
        prev = i - 1
        expr[f'lcd-elapsed{i}'] = f'calc(var(--lcd-dot{prev}) + 4 * var(--timer-go{i}) * var(--lcd-live))'
        expr[f'lcd-dot{i}'] = f'calc(mod(var(--lcd-elapsed{i}),456))'
        expr[f'lcd-line{i}'] = f'calc(mod(var(--lcd-line{prev}) + round(down,var(--lcd-elapsed{i}) / 456),154))'
        sample(str(i), 'var(--lcd-live)', 'var(--lcd-control)', f'var(--m{LYC})')
        expr[f'lcd-request{i}'] = f'calc(max(var(--lcd-request{prev}),var(--timer-go{i}) * var(--lcd-signal{i}) * (1 - var(--lcd-signal{prev}))))'
        expr[f'lcd-vblank{i}'] = f'calc(max(var(--lcd-vblank{prev}),var(--timer-go{i}) * var(--lcd-live) * ({equals(f"lcd-line{prev}",143)}) * ({equals(f"lcd-line{i}",144)})))'

    for addr in (LCDC, STAT, LYC):
        expr[f'io-hit{addr}'] = f'calc(var(--enabled) * var(--writing) * (({equals("address",addr)}) + var(--word) * ({equals("address2",addr)})))'
        expr[f'io-data{addr}'] = f'calc(({equals("address",addr)}) * var(--write) + var(--word) * ({equals("address2",addr)}) * var(--write2))'
        expr[f'lcd-new{addr}'] = f'calc(var(--m{addr}) + var(--io-hit{addr}) * (var(--io-data{addr}) - var(--m{addr})))'
    expr['lcd-new-live'] = f'calc(round(down,var(--lcd-new{LCDC}) / 128))'
    expr['lcd-new-control'] = f'calc(mod(round(down,var(--lcd-new{STAT}) / 8),16) * 8)'
    # Disabling resets position; enabling starts at line 0 / mode 2 in this model.
    expr['lcd-line-end'] = 'calc(var(--lcd-line6) * var(--lcd-new-live))'
    expr['lcd-dot-end'] = 'calc(var(--lcd-dot6) * var(--lcd-new-live))'
    sample('-end', 'var(--lcd-new-live)', 'var(--lcd-new-control)', f'var(--lcd-new{LYC})')
    expr['lcd-write-request'] = 'calc(var(--lcd-step) * var(--lcd-signal-end) * (1 - var(--lcd-signal6)))'
    # Clocked reads must not depend on CPU write data: read-modify-write I/O
    # would otherwise form a CSS dependency cycle. Merge write IRQs afterwards.
    states = {
        f'm{LCDC}': (0, f'var(--lcd-new{LCDC})'),
        f'm{STAT}': (132, 'var(--lcd-status-end)'),
        f'm{LY}': (0, 'var(--lcd-ly-end)'),
        f'm{LYC}': (0, f'var(--lcd-new{LYC})'),
        'lcd-line': (0, 'var(--lcd-line-end)'),
        'lcd-dot': (0, 'var(--lcd-dot-end)'),
        'lcd-stat': (0, 'var(--lcd-signal-end)'),
    }
    states = {name: (initial, f'calc(var(--{name}) + var(--lcd-step) * (({value}) - var(--{name})))')
              for name, (initial, value) in states.items()}
    return expr, states
