"""Bounded, feed-forward CSS execution. No program evaluation happens in Python."""
from cpu import machine, tile_css

STEPS = 128


def storage(states):
    declarations, read, execute = [], [], []
    for name, (initial, expression) in states.items():
        declarations.append(f'@property --next-{name} {{syntax:"<integer>";inherits:true;initial-value:{initial};}}')
        read.append(f'--{name}:var(--next-{name});')
        execute.append(f'--next-{name}:{expression};')
    return '\n'.join(declarations) + '\n.pipeline-read {' + ''.join(read) + '}\n.pipeline-execute {' + ''.join(execute) + '}\n'


def stylesheet(rom):
    css = machine(rom, storage, arithmetic=True)
    # The instruction decoder operates at every generic execution stage.
    css = css.replace('\n.machine {', '\n.pipeline-execute {')
    return css + tile_css(arithmetic=True)


def wrap(html, steps=STEPS):
    """Repeat generic CPU stages, not ROM-dependent states or instruction traces."""
    opening = ''.join(f'<div class="pipeline-read" data-stage="{i}"><div class="pipeline-execute">' for i in range(steps))
    html = html.replace('<div class="clock"><div class="machine">', '<div class="clock">' + opening + '<div class="pipeline-read machine">')
    return html.replace('</div></div>\n    </section>', '</div>' + '</div></div>' * steps + '</div>\n    </section>')
