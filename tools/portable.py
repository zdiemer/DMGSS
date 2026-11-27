"""Bounded, feed-forward CSS execution. No program evaluation happens in Python."""
from work_memory import pack_initial
from cpu import machine, tile_css, NATIVE_SUPPORT

STEPS = 128


def storage(states, initialize=True, native=True):
    declarations, read, execute, defaults, writes = [], [], [], [], []
    for name, (initial, expression) in states.items():
        read.append(f'--{name}:var(--next-{name});')
        if name.startswith('wram'):
            # Generic local write results materialize integers; RAM fields can
            # carry those plain tokens without thousands of global properties.
            defaults.append(f'--next-{name}:{initial};')
            index = int(name[4:]) // 2
            # Chromium needs a calculated query value for calculated indices.
            writes.append(f'@container style(--enabled:1) and style(--writing:1) and style(--wram-bus-address-index:calc({index})) {{.pipeline-read > .pipeline-execute {{--next-{name}:var(--wram-write-low);}}}}')
            writes.append(f'@container style(--enabled:1) and style(--writing:1) and style(--word:1) and style(--wram-bus-address2-index:calc({index})) {{.pipeline-read > .pipeline-execute {{--next-{name}:var(--wram-write-high);}}}}')
        else:
            declarations.append(f'@property --next-{name} {{syntax:"<integer>";inherits:true;initial-value:{initial};}}')
            execute.append(f'--next-{name}:{expression};')
    if native:
        # Large container-query write tables exhaust Chromium memory. CSS if()
        # updates the same words directly; older engines retain the query path.
        updates = ''.join(f'--next-{name}:{expression};' for name,(_,expression) in states.items() if name.startswith('wram'))
        write_css = f'@supports not {NATIVE_SUPPORT} {{\n' + '\n'.join(writes) + '}\n'
        write_css += f'@supports {NATIVE_SUPPORT} {{.pipeline-execute {{' + updates + '}}\n'
    else:
        write_css = '\n'.join(writes)
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
