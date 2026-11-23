"""Emit SM83 instruction semantics as CSS expressions (not an execution trace)."""
from rom import ROM

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


def pair_effects(pair, expression):
    """Split a wrapped word into simultaneous register writes from OLD state."""
    word = f'mod({expression}, 65536)'
    if pair == 'sp':
        return {'sp': f'calc({word})'}
    return {pair[0]: f'calc(round(down, ({word}) / 256))',
            pair[1]: f'calc(mod({word}, 256))'}


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


def stack_rom():
    """Original nested calls preserve BC while computing 8, then report success."""
    # Main calls outer four times. Outer saves the loop counter, increments A,
    # and calls inner, which increments A again and clobbers BC before returning.
    # Both return addresses and the saved BC live in ordinary emulated RAM.
    return [0x31,0x40,0xC0,0x06,4,0xAF,
            0xCD,0x17,1,0x05,0x20,0xFA,
            0xFE,8,0x20,6,0x3E,0xA5,0xEA,2,0xC0,0x76,0xD3,
            0xC5,0x3C,0xCD,0x1E,1,0xC1,0xC9,
            0x3C,0x01,0x34,0x12,0xC9]


def instruction_set():
    ops = {}
    def op(code, size=1, **effects):
        ops[code] = {'size': size, **effects}
    op(0x00)
    op(0x76, halted='1')  # Stops until reset; interrupts not yet implemented.
    for i, reg in enumerate(REGS):
        destination = reg or 'write'
        memory = {} if reg else {'access': '1', 'address': 'var(--hl)'}
        op(0x06 + i * 8, 2, **{destination: 'var(--imm)'}, **memory)
        value = f'var(--{reg})' if reg else 'var(--read)'
        inc = byte(value + ' + 1')
        dec = byte(value + ' - 1')
        carry = 'mod(var(--f), 32)'
        op(0x04 + i * 8, **{destination: f'calc({inc})', 'f': f'calc({zero(inc)} + round(down, mod({value}, 16) / 15) * 32 + {carry})'}, **memory)
        op(0x05 + i * 8, **{destination: f'calc({dec})', 'f': f'calc({zero(dec)} + 64 + (1 - min(1, mod({value}, 16))) * 32 + {carry})'}, **memory)
        for j, src in enumerate(REGS):
            if reg is None and src is None: continue  # 76 is HALT, not LD [HL],[HL].
            access = {} if reg and src else {'access': '1', 'address': 'var(--hl)'}
            op(0x40 + i * 8 + j, **{destination: f'var(--{src})' if src else 'var(--read)'}, **access)
    for i, pair in enumerate(('bc', 'de', 'hl', 'sp')):
        op(0x01 + i * 16, 3, **pair_effects(pair, 'var(--imm16)'))
        op(0x03 + i * 16, **pair_effects(pair, f'var(--{pair}) + 1'))
        op(0x0B + i * 16, **pair_effects(pair, f'var(--{pair}) - 1'))
        # ADD HL,rr preserves Z, clears N; carries come from bits 11 and 15.
        total = f'var(--hl) + var(--{pair})'
        half = f'round(down, (mod(var(--hl),4096) + mod(var(--{pair}),4096)) / 4096)'
        op(0x09 + i * 16, **pair_effects('hl', total),
           f=f'calc(var(--z) * 128 + ({half}) * 32 + round(down, ({total}) / 65536) * 16)')
    for i, pair in enumerate(('bc', 'de', 'hl', 'hl')):
        post = pair_effects('hl', f'var(--hl) + {1 if i == 2 else -1}') if i >= 2 else {}
        op(0x02 + i * 16, write='var(--a)', access='1', address=f'var(--{pair})', **post)
        op(0x0A + i * 16, a='var(--read)', access='1', address=f'var(--{pair})', **post)
    op(0xF9, sp='var(--hl)')
    op(0xE9, pc='var(--hl)')  # JP HL does not dereference memory.
    # Word transfers use two adjacent byte lanes, validated before either commits.
    # The lower address holds the low byte; PUSH stores at old SP-2 and SP-1.
    for i, pair in enumerate(('bc', 'de', 'hl', 'af')):
        op(0xC5 + i * 16, access='1', word='1',
           address='calc(mod(var(--sp) - 2, 65536))',
           write=f'var(--{pair[1]})', write2=f'var(--{pair[0]})',
           sp='calc(mod(var(--sp) - 2, 65536))')
        low = 'calc(round(down, var(--read) / 16) * 16)' if pair == 'af' else 'var(--read)'
        op(0xC1 + i * 16, access='1', word='1', address='var(--sp)',
           sp='calc(mod(var(--sp) + 2, 65536))',
           **{pair[0]: 'var(--read2)', pair[1]: low})
    conditions = ['1 - var(--z)', 'var(--z)', '1 - var(--carry)', 'var(--carry)']
    for code, condition in [(0xCD, '1'), *zip((0xC4, 0xCC, 0xD4, 0xDC), conditions)]:
        op(code, 3, access=f'calc({condition})', word='1',
           address='calc(mod(var(--sp) - 2, 65536))',
           write='calc(mod(var(--pc) + 3, 256))',
           write2='calc(round(down, mod(var(--pc) + 3, 65536) / 256))',
           sp=f'calc(mod(var(--sp) - 2 * ({condition}), 65536))',
           pc=f'calc(mod(var(--pc) + 3 + ({condition}) * (var(--imm16) - var(--pc) - 3), 65536))')
    for code, condition in [(0xC9, '1'), *zip((0xC0, 0xC8, 0xD0, 0xD8), conditions)]:
        op(code, access=f'calc({condition})', word='1', address='var(--sp)',
           sp=f'calc(mod(var(--sp) + 2 * ({condition}), 65536))',
           pc=f'calc(mod(var(--pc) + 1 + ({condition}) * (var(--read) + 256 * var(--read2) - var(--pc) - 1), 65536))')
    for code, condition in zip((0xC2, 0xCA, 0xD2, 0xDA), conditions):
        op(code, 3, pc=f'calc(mod(var(--pc) + 3 + ({condition}) * (var(--imm16) - var(--pc) - 3), 65536))')
    op(0x08, 3, access='1', word='1', write='calc(mod(var(--sp), 256))',
       write2='calc(round(down, var(--sp) / 256))')
    for code, pair in [(0xE8, 'sp'), (0xF8, 'hl')]:
        # Flags use the unsigned immediate's low nibble/byte even for e8 < 0.
        op(code, 2, **pair_effects(pair, 'var(--sp) + var(--signed)'),
           f='calc(round(down, (mod(var(--sp), 16) + mod(var(--imm), 16)) / 16) * 32 + round(down, (mod(var(--sp), 256) + var(--imm)) / 256) * 16)')
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
    op(0xC3, 3, pc='var(--imm16)')
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
    rom = rom if isinstance(rom, ROM) else ROM(rom, compact=False)
    props = {'opcode': 0, 'imm': 0, 'upper': 0, 'pc1': 257, 'pc2': 258,
             'imm16': 0, 'bc': 0, 'de': 0, 'hl': 0,
             'address': 0, 'signed': 0, 'z': 0, 'carry': 0, 'known': 0,
             'access': 0, 'writing': 0, 'writable': 0, 'readable': 0,
             'write': 0, 'valid': 0, 'read': 0, 'invalid': 0, 'enabled': 0,
             'word': 0, 'address2': 0, 'write2': 0, 'read2': 0,
             'writable2': 0, 'readable2': 0, 'valid2': 0}
    css = '\n'.join(f'@property --{k} {{syntax:"<integer>";inherits:true;initial-value:{v};}}' for k, v in props.items())
    expr = {
        'pc1': 'calc(mod(var(--pc) + 1, 65536))',
        'pc2': 'calc(mod(var(--pc) + 2, 65536))',
        'imm16': 'calc(var(--imm) + 256 * var(--upper))',
        **{pair: f'calc(var(--{pair[0]}) * 256 + var(--{pair[1]}))' for pair in ('bc', 'de', 'hl')},
        'address': choose('opcode', {k: v['address'] for k, v in ops.items() if 'address' in v}, 'var(--imm16)'),
        'address2': 'calc(mod(var(--address) + 1, 65536))',
        'signed': 'calc(var(--imm) - 256 * round(down, var(--imm) / 128))',
        'z': 'calc(round(down, var(--f) / 128))',
        'carry': 'calc(mod(round(down, var(--f) / 16), 2))',
        'known': choose('opcode', {k: 1 for k in ops}, 0),
        'access': choose('opcode', {k: v['access'] for k, v in ops.items() if 'access' in v}, 0),
        'word': choose('opcode', {k: v['word'] for k, v in ops.items() if 'word' in v}, 0),
        'writing': choose('opcode', {k: 'var(--access)' for k, v in ops.items() if 'write' in v}, 0),
        'write': choose('opcode', {k: v['write'] for k, v in ops.items() if 'write' in v}, 0),
        'write2': choose('opcode', {k: v['write2'] for k, v in ops.items() if 'write2' in v}, 0),
        'writable': choose('address', {i: 1 for i in RAM}, 0),
        'readable': rom.readable('address', choose, RAM),
        'valid': 'calc(var(--writing) * var(--writable) + (1 - var(--writing)) * var(--readable))',
        'read': rom.lookup('address', choose, {i: f'var(--m{i})' for i in RAM}, 'var(--readable)'),
        'writable2': choose('address2', {i: 1 for i in RAM}, 0),
        'readable2': rom.readable('address2', choose, RAM),
        'valid2': 'calc(var(--writing) * var(--writable2) + (1 - var(--writing)) * var(--readable2))',
        'read2': rom.lookup('address2', choose, {i: f'var(--m{i})' for i in RAM}, 'var(--readable2)'),
    }
    for name, pc in [('opcode', 'pc'), ('imm', 'pc1'), ('upper', 'pc2')]:
        expr[name] = rom.lookup(pc, choose)
    expr['invalid'] = 'calc(max(1 - var(--known), var(--access) * max(1 - var(--valid), var(--word) * (1 - var(--valid2)))))'
    expr['enabled'] = 'calc(var(--run, 1) * (1 - max(var(--halted), var(--fault), var(--invalid))))'
    css += '\n.machine {' + ''.join(f'--{k}:{v};' for k, v in expr.items()) + '}\n'
    states = {}
    stopped = 'style(--halted:1) or style(--fault:1)'
    invalid = 'style(--invalid:1)'
    for name in ['pc', 'a', 'b', 'c', 'd', 'e', 'h', 'l', 'f', 'sp', 'halted', 'fault', 'ticks']:
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
        result = f'if(style(--enabled:1) and style(--writing:1) and style(--address:{addr}):var(--write);style(--enabled:1) and style(--writing:1) and style(--word:1) and style(--address2:{addr}):var(--write2);else:var(--{name}))'
        if arithmetic:
            result = f'calc(var(--{name}) + var(--enabled) * var(--writing) * (({equals("address", addr)}) * (var(--write) - var(--{name})) + var(--word) * ({equals("address2", addr)}) * (var(--write2) - var(--{name}))))'
        states[name] = (0, result)
    css += storage(states)
    for name in ['pc', 'a', 'b', 'f', 'sp', 'ticks']:
        css += f'.register-{name}::after {{counter-reset:value var(--{name});content:counter(value);}}\n'
    for pair in ('bc', 'de', 'hl'):
        css += f'.register-{pair}::after {{counter-reset:value calc(var(--{pair[0]}) * 256 + var(--{pair[1]}));content:counter(value);}}\n'
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
    """A pointer loop copies original 2bpp ROM data to VRAM at runtime."""
    data = []
    for row in TILE:
        for plane in range(2):
            data.append(sum(((int(pixel) >> plane) & 1) << (7 - x) for x, pixel in enumerate(row)))
    # LD HL,010F; LD DE,8000; LD B,16
    # loop: LD A,[HL+]; LD [DE],A; INC DE; DEC B; JR NZ,loop; HALT
    return [0x21,0x0F,0x01,0x11,0x00,0x80,0x06,16,
            0x2A,0x12,0x13,0x05,0x20,0xFA,0x76] + data


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
