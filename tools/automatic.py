"""CSS scroll offsets retain state; timelines read it back into a generic CPU.

No ROM execution happens here. Re-snapping moves the inactive bank's markers
to the runtime result, then a one-pixel scroll cell commits the completed bank.
"""
from cpu import RAM, machine, tile_css
from portable import storage


def modulus(name):
    if name == 'serial-phase': return 512
    if name == 'serial-bits': return 8
    if name == 'serial-length': return 32
    if name == 'serial-count': return 65536
    return 2 if name in ('halted', 'fault', 'ime', 'ime-delay', 'halt-bug', 'timer-reload', 'clocked') else 65536 if name in ('pc', 'sp', 'ticks', 'tcycles') else 256


def generate(rom, initial=None):
    states = {}

    def collect(definitions):
        states.update(definitions)
        return storage(definitions)

    css = machine(rom, collect, arithmetic=True).replace('\n.machine {', '\n.pipeline-execute {')
    css = css.replace('calc(var(--ticks) + 1)', 'calc(mod(var(--ticks) + 1, 65536))')
    defaults = {name: (initial or {}).get(name, value) for name, (value, _) in states.items()}
    # Only ordinary physical RAM is packed. I/O and peripheral bookkeeping retain
    # their individual widths and semantics; the odd last HRAM byte stays alone.
    units, fields = {}, {}
    ram = set(RAM)
    paired = {address for address in ram if address % 2 == 0 and address + 1 in ram}
    for name in states:
        if name in fields:
            continue
        address = int(name[1:]) if name.startswith('m') and name[1:].isdigit() else -1
        members = (name, f'm{address+1}') if address in paired else (name,)
        unit = f'ram{address}' if len(members) == 2 else name
        units[unit] = members
        for lane, member in enumerate(members):
            fields[member] = (unit, lane)
    widths = {unit: 65536 if len(members) == 2 else modulus(unit) for unit, members in units.items()}
    starts = {unit: sum(defaults[member] * 256**lane for lane, member in enumerate(members))
              for unit, members in units.items()}
    results = {unit: f'var(--{members[0]})' if len(members) == 1 else
               f'var(--{members[0]}) + 256 * var(--{members[1]})'
               for unit, members in units.items()}
    names = ['select'] + [f'b{bank}-{name}' for bank in range(2) for name in units]
    # WebKit needs this scope on an ANCESTOR of the animated reader.
    rules = [css, 'body[data-automatic] {timeline-scope:' + ','.join('--t-' + n for n in names) + ';}']
    for name in ('select', 'ready', 'enabled-copy'):
        rules.append(f'@property --{name} {{syntax:"<integer>";inherits:true;initial-value:0;}}')
    rules.append('body[data-automatic] .clock {--run:0;--select:round(var(--raw-select));animation:none;}')
    rules.append('@supports (animation-timeline: --memory) and (timeline-scope: --memory) and (width:calc(1px * mod(round(down, abs(-3), 1), 2) * sign(1))) {\n' +
                 '@container style(--automatic-style:1) {\nbody[data-automatic] .clock {animation:' +
                 ','.join('read-' + n + ' 1s linear both' for n in names) + ';animation-timeline:' +
                 ','.join('--t-' + n for n in names) + ';}\n' +
                 'body[data-automatic] .power:checked ~ .clock {--run:1;}\n}}')
    cells = []
    for name in names:
        word = name.split('-', 1)[-1]
        limit = 1 if name == 'select' else widths[word] - 1
        # Even integer interpolation has tiny floating errors in WebKit. Round
        # the number explicitly before decoding, comparisons or marker layout.
        rules.append(f'@property --raw-{name} {{syntax:"<number>";inherits:true;initial-value:0;}}')
        rules.append(f'@keyframes read-{name} {{from{{--raw-{name}:0;}}to{{--raw-{name}:{limit};}}}}')
        rules.append(f'.memory-{name} {{scroll-timeline:--t-{name} y;}} .memory-{name} .memory-pad {{height:{limit + 20}px;}}')
        if name == 'select':
            target = 'var(--select) + var(--enabled-copy) * var(--ready) * (1 - 2 * var(--select))'
        else:
            bank = int(name[1])
            current = f'round(var(--raw-{name}))'
            # Zero scroll encodes the initial value (PC 0100, normally 0 elsewhere).
            result = f'mod(({results[word]}) - {starts[word]} + {limit + 1}, {limit + 1})'
            inactive = 'var(--select)' if bank == 0 else '(1 - var(--select))'
            target = f'{current} + var(--enabled-copy) * {inactive} * ({result} - {current})'
        rules.append(f'.memory-{name} .memory-mark {{top:calc(({target}) * 1px);}}')
        # No focusable controls: scroll cells must remain laid out but inaccessible
        # to pointer/keyboard input. display:none would deactivate their timelines.
        cells.append(f'<div class="scroll-memory memory-{name}" aria-hidden="true" tabindex="-1"><div class="memory-pad"><div class="memory-mark"></div></div></div>')
    seed, differences, display = [], [], []
    stored = {}
    for unit, members in units.items():
        value, width = starts[unit], widths[unit]
        for bank in range(2):
            decoded = f'mod(round(var(--raw-b{bank}-{unit})) + {value}, {width})'
            if len(members) == 2:
                # Resolve the packed word once before extracting either byte.
                prop = f'stored-b{bank}-{unit}'
                rules.append(f'@property --{prop} {{syntax:"<integer>";inherits:true;initial-value:{value};}}')
                seed.append(f'--{prop}:{decoded};')
                decoded = f'var(--{prop})'
            stored[bank,unit] = decoded
        a, b = stored[0,unit], stored[1,unit]
        # Equality of exact 16-bit pairs checks BOTH bytes before bank commit.
        differences.append(f'abs(({results[unit]}) - (({b}) * (1 - var(--select)) + ({a}) * var(--select)))')
    for name in states:
        unit, lane = fields[name]
        a, b = stored[0,unit], stored[1,unit]
        if len(units[unit]) == 2:
            a = f'mod(round(down,({a}) / {256**lane}),256)'
            b = f'mod(round(down,({b}) / {256**lane}),256)'
        value = defaults[name]
        rules.append(f'@property --seed-{name} {{syntax:"<integer>";inherits:true;initial-value:{value};}}')
        seed.append(f'--seed-{name}:calc(({a}) * (1 - var(--select)) + ({b}) * var(--select));--next-{name}:var(--seed-{name});')
        display.append(f'--{name}:var(--seed-{name});')
    rules.append('body[data-automatic] .clock {' + ''.join(seed) + '}')
    # Commit a halted/faulted RESULT before stopping. A halted SOURCE may still
    # wake on an enabled request or advance a live peripheral / pending reload.
    pending = ' + '.join(f'mod(round(down,var(--seed-m65295) / {1<<bit}),2) * mod(round(down,var(--seed-m65535) / {1<<bit}),2)' for bit in range(5))
    pending += ' + mod(round(down,var(--seed-m65287) / 4),2) + var(--seed-timer-reload) + round(down,var(--seed-m65282) / 128) * mod(var(--seed-m65282),2)'
    rules.append('.auto-output {--enabled-copy:calc(var(--run) * (1 - max(var(--seed-halted) * (1 - min(1,' + pending + ')), var(--seed-fault))));' +
                 '--ready:calc(1 - min(1, ' + ' + '.join(differences) + '));}')
    rules.append('body[data-automatic] .machine {' + ''.join(display) + '}')
    return '\n'.join(rules) + tile_css(arithmetic=True), ''.join(cells)
