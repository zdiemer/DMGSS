"""Reusable native HTML bit banks for explicitly user-clocked CSS checkpoints."""
from cpu import machine, tile_css
from portable import storage as pipeline_storage

WIDTHS = {'pc': 16, 'sp': 16, 'halted': 1, 'fault': 1, 'ticks': 16, 'tcycles': 16, 'ime': 1, 'ime-delay': 1, 'halt-bug': 1, 'timer-reload': 1, 'clocked': 1, 'serial-phase': 9, 'serial-bits': 3, 'serial-count': 16, 'serial-length': 5}


def counter_rom():
    # Four instructions per lap: RAM[C000]++ with 8-bit wrap, then branch back.
    return [0xFA, 0x00, 0xC0, 0x3C, 0xEA, 0x00, 0xC0, 0x18, 0xF7]


def generate(rom, initial=None):
    """Emit two bit banks and a generic copy selector, never execute the ROM."""
    states = {}
    def storage(definitions):
        if initial:
            definitions = {name: (initial.get(name, value), expression)
                           for name, (value, expression) in definitions.items()}
        states.update(definitions)
        return pipeline_storage(definitions)
    css = machine(rom, storage, arithmetic=True).replace('\n.machine {', '\n.pipeline-execute {')
    css += tile_css(arithmetic=True)
    bits = [(name, bit, (initial >> bit) & 1)
            for name, (initial, _) in states.items()
            for bit in range(WIDTHS.get(name, 8))]
    count = len(bits)
    inputs, controls = [], []
    css += '''
@property --bank-phase {syntax:"<integer>";inherits:true;initial-value:0}
@property --copy-index {syntax:"<integer>";inherits:true;initial-value:0}
@property --copy-group {syntax:"<integer>";inherits:true;initial-value:0}
@property --copy-slot {syntax:"<integer>";inherits:true;initial-value:0}
@property --copy-remaining {syntax:"<integer>";inherits:true;initial-value:0}
#commit:checked ~ .clock {--bank-phase:1}
'''
    def control(ident, classes, text):
        return f'<div class="copy-control {classes}"><label for="{ident}">{text}</label><a href="#{ident}">Keyboard: focus, then Space</a></div>'
    for bank in range(2):
        seed = []
        for name in states:
            value = ' + '.join(f'var(--b{bank}-{name}-{bit},0) * {1 << bit}' for bit in range(WIDTHS.get(name, 8)))
            seed.append(f'--seed{bank}-{name}:calc({value});')
        css += '.clock {' + ''.join(seed) + '}\n'
        for i, (name, bit, initial) in enumerate(bits):
            ident = f'b{bank}-{name}-{bit}'
            checked = ' checked' if initial else ''
            # Inputs precede the CPU and never disappear as a side effect of
            # activation. Labels and fragment focus links are native HTML.
            inputs.append(f'<input class="sr-only checkpoint-bit" type="checkbox" id="{ident}" tabindex="-1" autocomplete="off" aria-label="Save checkpoint {name} bit {bit}"{checked}>')
            controls.append(control(ident, f'bank{bank} copy-{i}', 'SAVE NEXT BIT'))
            css += f'#{ident}:checked ~ .clock {{--{ident}:1}}\n'
    css += '.clock {' + ''.join(f'--next-{name}:calc(var(--seed0-{name}) * (1 - var(--bank-phase)) + var(--seed1-{name}) * var(--bank-phase));' for name in states) + '}\n'
    differences = []
    for i, (name, bit, _) in enumerate(bits):
        # Only compare/copy into the INACTIVE bank. The source stays immutable
        # until the commit checkbox switches banks in one user action.
        result = f'mod(round(down,var(--{name}) / {1 << bit}),2)'
        target = f'var(--b1-{name}-{bit},0) * (1 - var(--bank-phase)) + var(--b0-{name}-{bit},0) * var(--bank-phase)'
        css += f'@property --diff-{i} {{syntax:"<integer>";inherits:true;initial-value:0}}\n'
        differences.append(f'--diff-{i}:calc(abs(({result}) - ({target})));')
        # Chromium can expose index 707 while failing style(--copy-index:707)
        # on this long min() expression. Small group/slot queries select the
        # same bit and work in both engines, including the last RAM bytes.
        css += f'@container style(--copy-group:{i // 32}) and style(--copy-slot:{i % 32}) {{.checkpoint-controls .copy-{i} {{display:block}}}}\n'
    css += '.checkpoint-values {' + ''.join(differences) + '}\n'
    css += '.checkpoint-select {--copy-remaining:calc(' + ' + '.join(f'var(--diff-{i})' for i in range(count)) + ');'
    css += '--copy-index:min(' + ','.join(f'{i} + (1 - var(--diff-{i})) * {count}' for i in range(count)) + f',{count});'
    css += '--copy-group:calc(round(down,var(--copy-index) / 32));--copy-slot:mod(var(--copy-index),32);}\n'
    css += '@container style(--copy-remaining:0) {.checkpoint-controls .commit-control {display:block}.save-hint {display:none}}\n'
    css += '.checkpoint-memory::after {counter-reset:value var(--m49152);content:counter(value);}\n'
    # Bookkeeping is finite so both banks have fixed size; hardware state keeps
    # its own 8/16-bit widths. The counter modulus is disclosed in the UI.
    css = css.replace('calc(var(--ticks) + 1)', f'calc(mod(var(--ticks) + 1,{1 << WIDTHS["ticks"]}))')
    inputs.append('<input class="sr-only checkpoint-bit" type="checkbox" id="commit" tabindex="-1" autocomplete="off" aria-label="Run next 128 instructions">')
    controls.append(control('commit', 'commit-control', 'RUN NEXT 128'))
    html = '<div class="checkpoint-values"><div class="checkpoint-select"><div class="checkpoint-controls">' + ''.join(controls)
    html += '<p class="save-hint"><span class="copy-remaining"></span> changed bits to save.<br>Tap once per bit, then run the next batch.</p></div></div></div>'
    return css, ''.join(inputs), html
