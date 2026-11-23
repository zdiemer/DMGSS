"""CSS scroll offsets retain state; timelines read it back into a generic CPU.

No ROM execution happens here. Re-snapping moves the inactive bank's markers
to the runtime result, then a one-pixel scroll cell commits the completed bank.
"""
from cpu import machine, tile_css
from portable import storage


def modulus(name):
    return 2 if name in ('halted', 'fault', 'ime', 'ime-delay', 'halt-bug') else 65536 if name in ('pc', 'sp', 'ticks') else 256


def generate(rom, initial=None):
    states = {}

    def collect(definitions):
        states.update(definitions)
        return storage(definitions)

    css = machine(rom, collect, arithmetic=True).replace('\n.machine {', '\n.pipeline-execute {')
    css = css.replace('calc(var(--ticks) + 1)', 'calc(mod(var(--ticks) + 1, 65536))')
    defaults = {name: (initial or {}).get(name, value) for name, (value, _) in states.items()}
    names = ['select'] + [f'b{bank}-{name}' for bank in range(2) for name in states]
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
        limit = 1 if name == 'select' else modulus(word) - 1
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
            result = f'mod(var(--{word}) - {defaults[word]} + {limit + 1}, {limit + 1})'
            inactive = 'var(--select)' if bank == 0 else '(1 - var(--select))'
            target = f'{current} + var(--enabled-copy) * {inactive} * ({result} - {current})'
        rules.append(f'.memory-{name} .memory-mark {{top:calc(({target}) * 1px);}}')
        # No focusable controls: scroll cells must remain laid out but inaccessible
        # to pointer/keyboard input. display:none would deactivate their timelines.
        cells.append(f'<div class="scroll-memory memory-{name}" aria-hidden="true" tabindex="-1"><div class="memory-pad"><div class="memory-mark"></div></div></div>')
    seed, differences, display = [], [], []
    for name in states:
        value, width = defaults[name], modulus(name)
        rules.append(f'@property --seed-{name} {{syntax:"<integer>";inherits:true;initial-value:{value};}}')
        a = f'mod(round(var(--raw-b0-{name})) + {value}, {width})'
        b = f'mod(round(var(--raw-b1-{name})) + {value}, {width})'
        seed.append(f'--seed-{name}:calc(({a}) * (1 - var(--select)) + ({b}) * var(--select));--next-{name}:var(--seed-{name});')
        differences.append(f'abs(var(--{name}) - (({b}) * (1 - var(--select)) + ({a}) * var(--select)))')
        display.append(f'--{name}:var(--seed-{name});')
    rules.append('body[data-automatic] .clock {' + ''.join(seed) + '}')
    # Commit a halted/faulted RESULT before stopping. A halted SOURCE may still
    # wake when its immutable IE/IF state has an enabled request.
    pending = ' + '.join(f'mod(round(down,var(--seed-m65295) / {1<<bit}),2) * mod(round(down,var(--seed-m65535) / {1<<bit}),2)' for bit in range(5))
    rules.append('.auto-output {--enabled-copy:calc(var(--run) * (1 - max(var(--seed-halted) * (1 - min(1,' + pending + ')), var(--seed-fault))));' +
                 '--ready:calc(1 - min(1, ' + ' + '.join(differences) + '));}')
    rules.append('body[data-automatic] .machine {' + ''.join(display) + '}')
    return '\n'.join(rules) + tile_css(arithmetic=True), ''.join(cells)
