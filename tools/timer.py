"""Emit DMG timer circuitry as CSS. No Python executes a timer or a ROM.

The CPU still retires atomically. Six generic M-cycle lanes advance peripherals
for its 4–24 T-cycle duration, then apply CPU writes at the final boundary.
HALT advances one M-cycle per stage while a timer/reload can still make progress.
"""
DIV, TIMA, TMA, TAC = range(0xFF04, 0xFF08)


def circuit(choose, equals):
    expr = {
        'timer-on': f'calc(mod(round(down,var(--m{TAC}) / 4),2))',
        'timer-period': choose('timer-select', {0:1024,1:16,2:64,3:256},1024),
        'timer-select': f'calc(mod(var(--m{TAC}),4))',
        'timer-live': 'calc(max(var(--timer-on),var(--timer-reload)))',
        'timer-idle': 'calc(var(--run,1) * (1 - var(--fault)) * var(--sleeping) * max(var(--timer-live),var(--serial-live)))',
        'timer-cycles': 'calc(var(--enabled) * var(--duration) + 4 * var(--timer-idle))',
        'timer-phase': f'calc(256 * var(--m{DIV}) + var(--div-low))',
        'timer-t0': f'var(--m{TIMA})',
        'timer-r0': 'var(--timer-reload)',
        'timer-request0': '0', 'timer-load0': '0',
    }
    for i in range(1,7):
        p = i-1
        expr.update({
            f'timer-go{i}': f'calc(min(1,max(0,var(--timer-cycles) / 4 - {p})))',
            f'timer-edge{i}': f'calc(var(--timer-go{i}) * var(--timer-on) * (round(down,(var(--timer-phase) + {4*i}) / var(--timer-period)) - round(down,(var(--timer-phase) + {4*p}) / var(--timer-period))))',
            f'timer-load{i}': f'calc(var(--timer-go{i}) * var(--timer-r{p}) + (1 - var(--timer-go{i})) * var(--timer-load{p}))',
            f'timer-t{i}': f'calc(var(--timer-go{i}) * var(--timer-r{p}) * var(--m{TMA}) + (1 - var(--timer-go{i}) * var(--timer-r{p})) * mod(var(--timer-t{p}) + var(--timer-edge{i}) * (1 - var(--timer-r{p})),256))',
            f'timer-r{i}': f'calc((1 - var(--timer-go{i})) * var(--timer-r{p}) + var(--timer-edge{i}) * (1 - var(--timer-r{p})) * ({equals(f"timer-t{p}",255)}))',
            f'timer-request{i}': f'calc(max(var(--timer-request{p}),var(--timer-go{i}) * var(--timer-r{p})))',
        })
    for addr in (DIV,TIMA,TMA,TAC):
        expr[f'io-hit{addr}'] = f'calc(var(--enabled) * var(--writing) * (({equals("address",addr)}) + var(--word) * ({equals("address2",addr)})))'
        expr[f'io-data{addr}'] = f'calc(({equals("address",addr)}) * var(--write) + var(--word) * ({equals("address2",addr)}) * var(--write2))'
    expr.update({
        'timer-end': 'calc(mod(var(--timer-phase) + var(--timer-cycles),65536))',
        'timer-new-phase': f'calc(var(--timer-end) * (1 - var(--io-hit{DIV})))',
        'timer-new-tac': f'calc(248 + mod(var(--m{TAC}) + var(--io-hit{TAC}) * (var(--io-data{TAC}) - var(--m{TAC})),8))',
        'timer-new-select': 'calc(mod(var(--timer-new-tac),4))',
        'timer-new-period': choose('timer-new-select',{0:1024,1:16,2:64,3:256},1024),
        'timer-new-on': 'calc(mod(round(down,var(--timer-new-tac) / 4),2))',
        # DIV reset or TAC changes can turn a high input into a low input.
        'timer-glitch': 'calc(var(--timer-on) * mod(round(down,var(--timer-end) / (var(--timer-period) / 2)),2) * (1 - var(--timer-new-on) * mod(round(down,var(--timer-new-phase) / (var(--timer-new-period) / 2)),2)))',
        'timer-bump': 'calc(var(--timer-glitch) * (1 - max(var(--timer-r6),var(--timer-load6))))',
        'timer-new-tma': f'calc(var(--m{TMA}) + var(--io-hit{TMA}) * (var(--io-data{TMA}) - var(--m{TMA})))',
        'timer-write-tima': f'calc(var(--io-hit{TIMA}) * (1 - var(--timer-load6)))',
        'timer-new-tima': f'calc(var(--timer-write-tima) * var(--io-data{TIMA}) + (1 - var(--timer-write-tima)) * (var(--timer-load6) * var(--timer-new-tma) + (1 - var(--timer-load6)) * mod(var(--timer-t6) + var(--timer-bump),256)))',
        'timer-new-reload': f'calc((1 - var(--timer-write-tima)) * max(var(--timer-r6),var(--timer-bump) * ({equals("timer-t6",255)})))',
    })
    states = {
        f'm{DIV}': (0,'calc(round(down,var(--timer-new-phase) / 256))'),
        'div-low': (0,'calc(mod(var(--timer-new-phase),256))'),
        f'm{TIMA}': (0,'var(--timer-new-tima)'),
        f'm{TMA}': (0,'var(--timer-new-tma)'),
        f'm{TAC}': (248,'var(--timer-new-tac)'),
        'timer-reload': (0,'var(--timer-new-reload)'),
        'clocked': (0,'calc(max(var(--clocked),min(1,var(--timer-cycles))))'),
    }
    return expr, states
