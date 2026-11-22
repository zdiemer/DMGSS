"""Emit SM83 instruction semantics as CSS expressions (not an execution trace)."""
REGS = ['b', 'c', 'd', 'e', 'h', 'l', None, 'a']
RAM = [*range(0x8000, 0x8010), *range(0xC000, 0xC040)]


def choose_native(key, values, default):
    return 'if(' + ''.join(f'style(--{key}:{k}):{v};' for k, v in values.items()) + f'else:{default})'


def equals(key, value):
    """Integer equality as a 0/1 arithmetic gate; no CSS if() required."""
    return f'max(0, 1 - abs(var(--{key}) - {value}))'


def choose_math(key, values, default):
    """Select one integer-keyed value; keys are unique and mutually exclusive."""
    terms = [f'({equals(key, k)}) * (({v}) - ({default}))' for k, v in values.items()]
    return 'calc((' + str(default) + ')' + ''.join(' + ' + t for t in terms) + ')'


def byte(expr):
    return f'mod({expr}, 256)'


def zero(expr):
    return f'(1 - min(1, {expr})) * 128'


def diagnostic():
    # Original test program. Labels are resolved here, instructions run in CSS.
    code, labels, refs = [], {}, []
    def emit(*values): code.extend(values)
    def label(name): labels[name] = len(code)
    def jr(op, target):
        emit(op, 0)
        refs.append((len(code) - 1, target))
    emit(0x3E, 0x0F, 0xC6, 1, 0xEA, 0, 0xC0, 0xAF, 0xFA, 0, 0xC0, 0xFE, 0x10)
    jr(0x20, 'fail')
    emit(0x06, 4)
    label('loop')
    emit(0x3C, 0x05)
    jr(0x20, 'loop')
    emit(0xEA, 1, 0xC0, 0x3E, 0xA5, 0xEA, 2, 0xC0, 0x76)
    label('fail')
    emit(0x3E, 0xFF, 0xEA, 2, 0xC0, 0x76)
    for index, target in refs:
        code[index] = (labels[target] - (index + 1)) % 256
    return code


def instruction_set():
    ops = {}
    def op(code, size=1, **effects):
        ops[code] = {'size': size, **effects}
    op(0x00)
    op(0x76, halted='1')  # Stops until reset; interrupts not yet implemented.
    for i, reg in enumerate(REGS):
        if reg is None: continue
        op(0x06 + i * 8, 2, **{reg: 'var(--imm)'})
        value = f'var(--{reg})'
        inc = byte(value + ' + 1')
        dec = byte(value + ' - 1')
        carry = 'mod(var(--f), 32)'
        op(0x04 + i * 8, **{reg: f'calc({inc})', 'f': f'calc({zero(inc)} + round(down, mod({value}, 16) / 15) * 32 + {carry})'})
        op(0x05 + i * 8, **{reg: f'calc({dec})', 'f': f'calc({zero(dec)} + 64 + (1 - min(1, mod({value}, 16))) * 32 + {carry})'})
        for j, src in enumerate(REGS):
            if src is not None:
                op(0x40 + i * 8 + j, **{reg: f'var(--{src})'})
    for code, mode in [(0xC6, 'add'), (0xD6, 'sub'), (0xFE, 'cp')]:
        a, b = 'var(--a)', 'var(--imm)'
        raw = f'{a} + {b}' if mode == 'add' else f'{a} - {b}'
        result = byte(raw)
        if mode == 'add':
            half = f'round(down, (mod({a},16) + mod({b},16)) / 16)'
            carry = f'round(down, ({raw}) / 256)'
        else:
            half = f'max(0, sign(mod({b},16) - mod({a},16)))'
            carry = f'max(0, sign({b} - {a}))'
        effects = {'f': f'calc({zero(result)} + {64 if mode != "add" else 0} + ({half}) * 32 + ({carry}) * 16)'}
        if mode != 'cp': effects['a'] = f'calc({result})'
        op(code, 2, **effects)
    op(0xAF, a='0', f='128')
    op(0xC3, 3, pc='var(--address)')
    target = 'calc(mod(var(--pc) + 2 + var(--signed), 65536))'
    op(0x18, 2, pc=target)
    for code, condition in [(0x20, '1 - var(--z)'), (0x28, 'var(--z)'), (0x30, '1 - var(--carry)'), (0x38, 'var(--carry)')]:
        op(code, 2, pc=f'calc(mod(var(--pc) + 2 + ({condition}) * var(--signed), 65536))')
    op(0xEA, 3, write='var(--a)', access='1')
    op(0xFA, 3, a='var(--read)', access='1')
    return ops


def machine(rom, storage, arithmetic=False):
    choose = choose_math if arithmetic else choose_native
    ops = instruction_set()
    props = {'opcode': 0, 'imm': 0, 'upper': 0, 'pc1': 257, 'pc2': 258,
             'address': 0, 'signed': 0, 'z': 0, 'carry': 0, 'known': 0,
             'access': 0, 'valid': 0, 'read': 0, 'invalid': 0, 'enabled': 0}
    css = '\n'.join(f'@property --{k} {{syntax:"<integer>";inherits:true;initial-value:{v};}}' for k, v in props.items())
    expr = {
        'pc1': 'calc(mod(var(--pc) + 1, 65536))',
        'pc2': 'calc(mod(var(--pc) + 2, 65536))',
        'address': 'calc(var(--imm) + 256 * var(--upper))',
        'signed': 'calc(var(--imm) - 256 * round(down, var(--imm) / 128))',
        'z': 'calc(round(down, var(--f) / 128))',
        'carry': 'calc(mod(round(down, var(--f) / 16), 2))',
        'known': choose('opcode', {k: 1 for k in ops}, 0),
        'access': choose('opcode', {k: v['access'] for k, v in ops.items() if 'access' in v}, 0),
        'valid': choose('address', {i: 1 for i in RAM}, 0),
        'read': choose('address', {i: f'var(--m{i})' for i in RAM}, 255),
    }
    for name, pc in [('opcode', 'pc'), ('imm', 'pc1'), ('upper', 'pc2')]:
        expr[name] = choose(pc, {256 + i: b for i, b in enumerate(rom)}, 255)
    expr['invalid'] = 'calc(max(1 - var(--known), var(--access) * (1 - var(--valid))))'
    expr['enabled'] = 'calc(var(--run, 1) * (1 - max(var(--halted), var(--fault), var(--invalid))))'
    css += '\n.machine {' + ''.join(f'--{k}:{v};' for k, v in expr.items()) + '}\n'
    states = {}
    stopped = 'style(--halted:1) or style(--fault:1)'
    invalid = 'style(--known:0) or (style(--access:1) and style(--valid:0))'
    for name in ['pc', 'a', 'b', 'c', 'd', 'e', 'h', 'l', 'f', 'halted', 'fault', 'ticks']:
        initial = 256 if name == 'pc' else 0
        default = f'var(--{name})'
        if name == 'ticks': default = 'calc(var(--ticks) + 1)'
        changes = {}
        for code, effects in ops.items():
            if name == 'pc':
                changes[code] = effects.get('pc', f'calc(mod(var(--pc) + {effects["size"]}, 65536))')
            elif name in effects: changes[code] = effects[name]
        calc = choose('opcode', changes, default) if changes else default
        on_invalid = '1' if name == 'fault' else f'var(--{name})'
        result = f'if({stopped}:var(--{name});{invalid}:{on_invalid};else:{calc})'
        if arithmetic:
            result = f'calc(var(--{name}) + var(--enabled) * (({calc}) - var(--{name})))'
            if name == 'fault':
                result = 'calc(max(var(--fault), var(--run, 1) * (1 - var(--halted)) * var(--invalid)))'
        states[name] = (initial, result)
    for addr in RAM:
        name = f'm{addr}'
        result = f'if({stopped}:var(--{name});style(--opcode:234) and style(--address:{addr}):var(--a);else:var(--{name}))'
        if arithmetic:
            result = f'calc(var(--{name}) + var(--enabled) * ({equals("opcode", 234)}) * ({equals("address", addr)}) * (var(--a) - var(--{name})))'
        states[name] = (0, result)
    css += storage(states)
    for name in ['pc', 'a', 'b', 'f', 'ticks']:
        css += f'.register-{name}::after {{counter-reset:value var(--{name});content:counter(value);}}\n'
    css += '''
@container style(--halted:1) {.running-message{display:none}.halt-message{display:block}}
@container style(--fault:1) {.running-message{display:none}.fault-message{display:block}}
@container style(--m49154:165) {.halt-message .passed{display:inline-block}.halt-message .stopped{display:none}}
'''
    return css


TILE = [
    '00333300',
    '03111130',
    '31211213',
    '31111113',
    '31211213',
    '31122113',
    '03111130',
    '00333300',
]


def tile_rom():
    """Original 8x8 image encoded as ordinary DMG 2bpp bytes, written by the CPU."""
    data = []
    for row in TILE:
        for plane in range(2):
            data.append(sum(((int(pixel) >> plane) & 1) << (7 - x) for x, pixel in enumerate(row)))
    code = []
    for offset, value in enumerate(data):
        code.extend([0x3E, value, 0xEA, offset, 0x80])
    return code + [0x76]


def tile_css(arithmetic=False):
    css = '@property --shade {syntax:"<integer>";inherits:false;initial-value:0;}\n'
    colors = {0: '#b1c37e', 1: '#8baf62', 2: '#527547', 3: '#31452c'}
    for y in range(8):
        for x in range(8):
            bit = 2 ** (7 - x)
            shade = f'calc(mod(round(down, var(--m{0x8000 + y * 2}) / {bit}), 2) + 2 * mod(round(down, var(--m{0x8001 + y * 2}) / {bit}), 2))'
            css += f'.pixel-{y * 8 + x} {{--shade:{shade};}}\n'
    if arithmetic:
        channels = [choose_math('shade', {k: int(v[i:i+2], 16) for k, v in colors.items()}, int(colors[0][i:i+2], 16)) for i in [1, 3, 5]]
        css += '.tile-grid i {background:rgb(' + ' '.join(channels) + '); }\n'
    else:
        css += '.tile-grid i {background:' + choose_native('shade', colors, colors[0]) + ';}\n'
    return css
