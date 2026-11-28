"""Bounded, feed-forward CSS execution. No program evaluation happens in Python."""
from work_memory import pack_initial
from cpu import machine, tile_css

STEPS = 128


def storage(states, initialize=True):
    declarations, read, execute, defaults = [], [], [], []
    pages = {}
    for name, (initial, expression) in states.items():
        read.append(f'--{name}:var(--next-{name});')
        if name.startswith(('wram','vram')):
            # Generic local write results materialize integers; RAM fields can
            # carry those plain tokens without thousands of global properties.
            defaults.append(f'--next-{name}:{initial};')
            address = int(name[4:])
            pages.setdefault(address // 256, []).append(name)
        else:
            declarations.append(f'@property --next-{name} {{syntax:"<integer>";inherits:true;initial-value:{initial};}}')
            execute.append(f'--next-{name}:{expression};')
    # Materialize writes through 256 reusable typed slots, not one
    # registered property/query per physical word. Separate lane slots keep
    # simultaneous writes to different pages from overwriting each other's values.
    slots = sorted({int(name[4:]) // 2 % 128 for names in pages.values() for name in names})
    write_css = '\n'.join(f'@property --write-word-{lane}-{slot} {{syntax:"<integer>";inherits:false;initial-value:0;}}' for lane in (0,1) for slot in slots)
    for page, names in pages.items():
        for lane, bus in enumerate(('address','address2')):
            assignments = []
            for name in names:
                index = int(name[4:]) // 2
                result = f'write-word-{lane}-{index % 128}'
                first = f'max(0,1 - abs(var(--ram-bus-address-index) - {index}))'
                second = f'max(0,1 - abs(var(--ram-bus-address2-index) - {index}))'
                assignments.append(f'--{result}:calc(var(--{name}) + {first} * var(--ram-delta) + var(--word) * {second} * var(--ram-delta2));--next-{name}:var(--{result});')
            word = ' and style(--word:1)' if lane else ''
            condition = f'style(--enabled:1) and style(--writing:1){word} and style(--ram-bus-{bus}-page:calc({page}))'
            write_css += f'\n@container {condition} {{.pipeline-read > .pipeline-execute {{' + ''.join(assignments) + '}}'
    seed = '\nbody {' + ''.join(defaults) + '}' if initialize else ''
    return write_css + '\n'.join(declarations) + seed + '\n.pipeline-read {' + ''.join(read) + '}\n.pipeline-execute {' + ''.join(execute) + '}\n'



def stylesheet(rom, initial=None):
    def seeded(definitions):
        seeds = pack_initial(initial)
        return storage({name: (seeds.get(name,value), expression) for name,(value,expression) in definitions.items()})
    css = machine(rom, seeded, arithmetic=True)
    # The instruction decoder operates at every generic execution stage.
    css = css.replace('\n.machine {', '\n.pipeline-read {')
    return css + tile_css(arithmetic=True)


def wrap(html, steps=STEPS):
    """Repeat generic CPU stages, not ROM-dependent states or instruction traces."""
    opening = ''.join(f'<div class="pipeline-read" data-stage="{i}"><div class="pipeline-execute">' for i in range(steps))
    html = html.replace('<div class="clock"><div class="machine">', '<div class="clock">' + opening + '<div class="pipeline-read machine">')
    return html.replace('</div></div>\n    </section>', '</div>' + '</div></div>' * steps + '</div>\n    </section>')
