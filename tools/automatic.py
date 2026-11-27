"""CSS scroll offsets retain state; timelines read it back into a generic CPU.

No ROM execution happens here. Re-snapping moves the inactive bank's markers
to the runtime result, then a one-pixel scroll cell commits the completed bank.
"""
from work_memory import pack_initial
from cpu import RAM, machine, tile_css
from portable import storage


def modulus(name):
    if name == 'mbc-bank': return 32
    if name.startswith('wram'): return 65536
    if name == 'serial-phase': return 512
    if name == 'serial-bits': return 8
    if name == 'serial-length': return 32
    if name == 'serial-count': return 65536
    return 2 if name in ('halted', 'fault', 'ime', 'ime-delay', 'halt-bug', 'timer-reload', 'clocked') else 65536 if name in ('pc', 'sp', 'ticks', 'tcycles') else 256


def generate(rom, initial=None, arithmetic=True):
    initial = pack_initial(initial)
    states = {}

    def collect(definitions):
        states.update(definitions)
        return storage(definitions, initialize=False)

    css = machine(rom, collect, arithmetic=arithmetic).replace('\n.machine {', '\n.pipeline-read {')
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
    # Each reader owns at most 64 raw timelines. Materialize decoded source and
    # inactive words through reusable local integers, then expose their values, rather than inheriting thousands of raw
    # animation values through every later reader and CPU stage.
    batches = [list(units)[i:i+32] for i in range(0,len(units),32)]
    groups = [['select']] + [[f'b{bank}-{unit}' for unit in batch for bank in range(2)] for batch in batches]
    names = [name for group in groups for name in group]
    rules = [css, 'body[data-automatic] {timeline-scope:' + ','.join('--t-' + n for n in names) + ';}']
    for name in ('select', 'ready', 'enabled-copy'):
        rules.append(f'@property --{name} {{syntax:"<integer>";inherits:true;initial-value:0;}}')
    rules.append('body[data-automatic] .clock {--run:0;animation:none;} .auto-reader-0 {--select:round(var(--raw-0));} .auto-reader,.auto-seed {display:contents;}')
    for i in range(64):
        rules.append(f'@property --raw-{i} {{syntax:"<number>";inherits:false;initial-value:0;}}')
    for i in range(32):
        for prefix in ('source-word','inactive-word','source-low','source-high'):
            rules.append(f'@property --{prefix}-{i} {{syntax:"<integer>";inherits:false;initial-value:0;}}')
    keyframes = set()
    rules.append('@supports (animation-timeline: --memory) and (timeline-scope: --memory) and (width:calc(1px * mod(round(down, abs(-3), 1), 2) * sign(1))) {\n@container style(--automatic-style:1) {')
    for i, group in enumerate(groups):
        animations=[]
        for slot,name in enumerate(group):
            limit=1 if name=='select' else widths[name.split('-',1)[-1]]-1
            keyframes.add((slot,limit))
            animations.append(f'read-{slot}-{limit} 1s linear both')
        rules.append(f'.auto-reader-{i} {{animation:' + ','.join(animations) + ';animation-timeline:' + ','.join('--t-' + n for n in group) + ';}')
    rules.append('body[data-automatic] .power:checked ~ .clock {--run:1;}}}')
    for slot,limit in sorted(keyframes):
        rules.append(f'@keyframes read-{slot}-{limit} {{from{{--raw-{slot}:0;}}to{{--raw-{slot}:{limit};}}}}')
    cells = []
    for name in names:
        unit = name.split('-',1)[-1]
        limit = 1 if name == 'select' else widths[unit]-1
        rules.append(f'.memory-{name} {{scroll-timeline:--t-{name} y;}} .memory-{name} .memory-pad {{height:{limit+20}px;}}')
        if name == 'select':
            target = 'var(--select) + var(--enabled-copy) * var(--ready) * (1 - 2 * var(--select))'
            bank_class = ''
        else:
            target = f'mod(({results[unit]}) - {starts[unit]} + {limit+1}, {limit+1})'
            bank_class = f' memory-bank-{name[1]}'
        rules.append(f'.memory-{name} .memory-mark {{top:calc(({target}) * 1px);}}')
        cells.append(f'<div class="scroll-memory memory-{name}{bank_class}" aria-hidden="true" tabindex="-1"><div class="memory-pad"><div class="memory-mark"></div></div></div>')
    # Marker movement must never resnap the source bank, including while paused
    # or after a committed HALT/fault. The inactive bank alone copies results.
    rules.append('@container style(--select:0) {body[data-automatic] .memory-bank-0 {scroll-snap-type:none}} @container style(--select:1) {body[data-automatic] .memory-bank-1 {scroll-snap-type:none}} @container style(--enabled-copy:0) {body[data-automatic] .scroll-memory {scroll-snap-type:none}}')
    seed, differences, display = [], [], []
    for i, batch in enumerate(batches,1):
        bindings = []
        for slot,unit in enumerate(batch):
            members, value, width = units[unit], starts[unit], widths[unit]
            a,b = (f'mod(round(var(--raw-{slot*2+bank})) + {value},{width})' for bank in range(2))
            bindings.append(f'--source-word-{slot}:calc(({a}) * (1 - var(--select)) + ({b}) * var(--select));')
            bindings.append(f'--inactive-word-{slot}:calc(({b}) * (1 - var(--select)) + ({a}) * var(--select));--inactive-{unit}:var(--inactive-word-{slot});')
            differences.append(f'abs(({results[unit]}) - var(--inactive-{unit}))')
            for lane,name in enumerate(members):
                source=f'source-word-{slot}'
                if len(members)==2:
                    source=f'source-{"low" if lane==0 else "high"}-{slot}'
                    bindings.append(f'--{source}:mod(round(down,var(--source-word-{slot}) / {256**lane}),256);')
                bindings.append(f'--seed-{name}:var(--{source});')
                seed.append(f'--next-{name}:var(--seed-{name});')
                display.append(f'--{name}:var(--seed-{name});')
            if unit.startswith('wram'):
                rules.append(f'@container style(--{unit}:{value}) and style(--seed-{unit}:{value}) and style(--inactive-{unit}:{value}) {{.memory-b0-{unit},.memory-b1-{unit}{{display:none}}}}')
        rules.append(f'.auto-reader-{i} {{' + ''.join(bindings) + '}')
    rules.append('body[data-automatic] .auto-seed {' + ''.join(seed) + '}')
    # Commit a halted/faulted RESULT before stopping. A halted SOURCE may still
    # wake on an enabled request or advance a live peripheral / pending reload.
    pending = ' + '.join(f'mod(round(down,var(--seed-m65295) / {1<<bit}),2) * mod(round(down,var(--seed-m65535) / {1<<bit}),2)' for bit in range(5))
    pending += ' + mod(round(down,var(--seed-m65287) / 4),2) + var(--seed-timer-reload) + round(down,var(--seed-m65282) / 128) * mod(var(--seed-m65282),2)'
    rules.append('.auto-output {--enabled-copy:calc(var(--run) * (1 - max(var(--seed-halted) * (1 - min(1,' + pending + ')), var(--seed-fault))));' +
                 '--ready:calc(1 - min(1, ' + ' + '.join(differences) + '));}')
    rules.append('body[data-automatic] .machine {' + ''.join(display) + '}')
    return '\n'.join(rules) + tile_css(arithmetic=arithmetic), ''.join(cells), len(groups)
