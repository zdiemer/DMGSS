"""Emit SM83 instruction semantics as CSS expressions (not an execution trace)."""
from rom import ROM
from timing import duration
from timer import DIV, TIMA, TMA, TAC, circuit
from serial_io import SB, SC, circuit as serial_circuit, monitor_css

REGS = ['b', 'c', 'd', 'e', 'h', 'l', None, 'a']
RAM = [*range(0x8000, 0x8010), *range(0xC000, 0xC040), *range(0xFF80, 0xFFFF)]
IF, IE = 0xFF0F, 0xFFFF
MEMORY = [*RAM, IF, IE, DIV, TIMA, TMA, TAC, SB, SC]


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
    op(0x76, halted='calc(1 - var(--halt-trigger))', **{'halt-bug':'var(--halt-trigger)'})
    op(0xF3, ime='0', **{'ime-delay':'0'})
    op(0xFB, **{'ime-delay':'1'})
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
    for store, load, size, offset in [(0xE0,0xF0,2,'imm'), (0xE2,0xF2,1,'c')]:
        address = f'calc(65280 + var(--{offset}))'
        op(store, size, access='1', address=address, write='var(--a)')
        op(load, size, access='1', address=address, a='var(--read)')
    for vector in range(0, 0x40, 8):
        op(0xC7 + vector, access='1', word='1',
           address='calc(mod(var(--sp) - 2, 65536))',
           write='calc(mod(var(--pc) + 1, 256))',
           write2='calc(round(down, mod(var(--pc) + 1, 65536) / 256))',
           sp='calc(mod(var(--sp) - 2, 65536))', pc=str(vector))
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
    for code, condition in [(0xC9, '1'), (0xD9, '1'), *zip((0xC0, 0xC8, 0xD0, 0xD8), conditions)]:
        op(code, access=f'calc({condition})', word='1', address='var(--sp)',
           sp=f'calc(mod(var(--sp) + 2 * ({condition}), 65536))',
           pc=f'calc(mod(var(--pc) + 1 + ({condition}) * (var(--read) + 256 * var(--read2) - var(--pc) - 1), 65536))')
    ops[0xD9].update(ime='1', **{'ime-delay':'0'})
    for code, condition in zip((0xC2, 0xCA, 0xD2, 0xDA), conditions):
        op(code, 3, pc=f'calc(mod(var(--pc) + 3 + ({condition}) * (var(--imm16) - var(--pc) - 3), 65536))')
    op(0x08, 3, access='1', word='1', write='calc(mod(var(--sp), 256))',
       write2='calc(round(down, var(--sp) / 256))')
    for code, pair in [(0xE8, 'sp'), (0xF8, 'hl')]:
        # Flags use the unsigned immediate's low nibble/byte even for e8 < 0.
        op(code, 2, **pair_effects(pair, 'var(--sp) + var(--signed)'),
           f='calc(round(down, (mod(var(--sp), 16) + mod(var(--imm), 16)) / 16) * 32 + round(down, (mod(var(--sp), 256) + var(--imm)) / 256) * 16)')
    # The eight ALU families share one operand/result network. Keeping bitwise
    # arithmetic out of each opcode arm avoids multiplying the CSS expression.
    for family, immediate in enumerate((0xC6,0xCE,0xD6,0xDE,0xE6,0xEE,0xF6,0xFE)):
        effects = {'f': 'var(--alu-flags)'}
        if family != 7:
            effects['a'] = 'var(--alu-result)'
        op(immediate, 2, **effects)
        for index, reg in enumerate(REGS):
            access = {} if reg else {'access': '1', 'address': 'var(--hl)'}
            op(0x80 + family * 8 + index, **effects, **access)
    for code, direction, through_carry in [(0x07,'left',False),(0x0F,'right',False),
                                            (0x17,'left',True),(0x1F,'right',True)]:
        outgoing = 'round(down, var(--a) / 128)' if direction == 'left' else 'mod(var(--a), 2)'
        incoming = 'var(--carry)' if through_carry else outgoing
        result = f'mod(var(--a) * 2 + ({incoming}), 256)' if direction == 'left' else f'round(down, var(--a) / 2) + ({incoming}) * 128'
        # Unlike CB rotations, accumulator rotations always clear Z.
        op(code, a=f'calc({result})', f=f'calc(({outgoing}) * 16)')
    op(0x27, a='var(--daa-result)',
       f=f'calc({zero("var(--daa-result)")} + var(--subtract) * 64 + var(--daa-high) * 16)')
    op(0x2F, a='calc(255 - var(--a))', f='calc(var(--z) * 128 + 96 + var(--carry) * 16)')
    op(0x37, f='calc(var(--z) * 128 + 16)')
    op(0x3F, f='calc(var(--z) * 128 + (1 - var(--carry)) * 16)')
    # CB is decoded as one two-byte instruction. BIT reads but never writes;
    # every other memory form validates a write before any state can commit.
    op(0xCB, 2, access=f'calc({equals("cb-index", 6)})', address='var(--hl)',
       writing='calc(var(--access) * var(--cb-mutate))', write='var(--cb-result)',
       f='var(--cb-flags)',
       **{reg: f'calc(var(--{reg}) + var(--cb-mutate) * ({equals("cb-index", i)}) * (var(--cb-result) - var(--{reg})))'
          for i, reg in enumerate(REGS) if reg})
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
    timer_expr, timer_states = circuit(choose, equals)
    serial_expr, serial_states = serial_circuit(equals)
    read_memory = {i: f'var(--m{i})' for i in MEMORY}
    # Peripheral data reads observe the final M-cycle. Opcode/immediate fetch still
    # uses the old bank; full bus scheduling is a separate milestone.
    read_memory.update({DIV:'calc(round(down,var(--timer-end) / 256))',
                        TIMA:'var(--timer-t6)', IF:'var(--hardware-if)',
                        SB:'var(--serial-sb)', SC:'var(--serial-sc)'})
    ops = instruction_set()
    # A service step is not an opcode or a retired instruction. It uses the
    # same atomic two-lane stack path and takes one generic pipeline stage.
    ops[256] = dict(size=0, access='1', word='1',
        address='calc(mod(var(--sp) - 2, 65536))',
        write='calc(mod(var(--exec-pc), 256))',
        write2='calc(round(down, var(--exec-pc) / 256))',
        sp='calc(mod(var(--sp) - 2, 65536))', pc='var(--irq-vector)',
        ime='0', ticks='var(--ticks)', **{'ime-delay':'0'})
    rom = rom if isinstance(rom, ROM) else ROM(rom, compact=False)
    props = {'opcode': 0, 'raw-opcode': 0, 'exec-pc': 256, 'duration': 0,
             'pending-mask': 0, 'pending': 0, 'irq': 0, 'irq-mask': 0,
             'irq-vector': 64, 'halt-trigger': 0, 'sleeping': 0, 'imm': 0, 'upper': 0, 'pc1': 257, 'pc2': 258,
             'imm16': 0, 'bc': 0, 'de': 0, 'hl': 0,
             'size': 1, 'fetch0': 0, 'fetch1': 0, 'fetch2': 0, 'fetch-valid': 0,
             'address': 0, 'signed': 0, 'z': 0, 'carry': 0, 'known': 0,
             'access': 0, 'writing': 0, 'writable': 0, 'readable': 0,
             'write': 0, 'valid': 0, 'read': 0, 'invalid': 0, 'enabled': 0,
             'word': 0, 'address2': 0, 'write2': 0, 'read2': 0,
             'writable2': 0, 'readable2': 0, 'valid2': 0,
             'alu-index': 0, 'alu-op': 0, 'alu-input': 0, 'alu-cin': 0,
             'alu-sub': 0, 'alu-wide': 0, 'alu-result': 0, 'alu-flags': 0,
             'subtract': 0, 'half-carry': 0, 'daa-high': 0, 'daa-low': 0, 'daa-result': 0,
             **dict.fromkeys(('cb-index','cb-group','cb-kind','cb-input','cb-weight',
                              'cb-bit','cb-mutate','cb-rotate','cb-carry','cb-result','cb-flags'), 0)}
    props.update(dict.fromkeys(timer_expr,0))
    props.update(dict.fromkeys(serial_expr,0))
    props.update({'timer-if':224,'hardware-if':224,'resume':0})
    css = '\n'.join(f'@property --{k} {{syntax:"<integer>";inherits:true;initial-value:{v};}}' for k, v in props.items())
    expr = {
        'duration': duration(choose),
        'exec-pc': 'calc(mod(var(--pc) - var(--halt-bug), 65536))',
        'pc1': 'calc(mod(var(--exec-pc) + 1, 65536))',
        'pc2': 'calc(mod(var(--exec-pc) + 2, 65536))',
        'pending-mask': 'calc(' + ' + '.join(f'mod(round(down,var(--m{IF}) / {1<<bit}),2) * mod(round(down,var(--m{IE}) / {1<<bit}),2) * {1<<bit}' for bit in range(5)) + ')',
        'pending': 'calc(min(1,var(--pending-mask)))',
        'irq': 'calc(var(--ime) * var(--pending))',
        'irq-mask': choose('pending-mask', {i:i & -i for i in range(1,32)}, 0),
        'irq-vector': choose('irq-mask', {1<<i:64+8*i for i in range(5)}, 64),
        'halt-trigger': 'calc((1 - var(--ime)) * var(--pending))',
        'sleeping': 'calc(var(--halted) * (1 - var(--pending)))',
        'opcode': 'calc(var(--raw-opcode) + var(--irq) * (256 - var(--raw-opcode)))',
        'imm16': 'calc(var(--imm) + 256 * var(--upper))',
        **{pair: f'calc(var(--{pair[0]}) * 256 + var(--{pair[1]}))' for pair in ('bc', 'de', 'hl')},
        'address': choose('opcode', {k: v['address'] for k, v in ops.items() if 'address' in v}, 'var(--imm16)'),
        'address2': 'calc(mod(var(--address) + 1, 65536))',
        'signed': 'calc(var(--imm) - 256 * round(down, var(--imm) / 128))',
        'z': 'calc(round(down, var(--f) / 128))',
        'carry': 'calc(mod(round(down, var(--f) / 16), 2))',
        'known': choose('opcode', {k: 1 for k in ops}, 0),
        'size': choose('opcode', {k: v['size'] for k, v in ops.items() if v['size'] != 1}, 1),
        'fetch-valid': 'calc(min(var(--fetch0), 1 - min(1, max(0, var(--size) - 1)) * (1 - var(--fetch1)), 1 - max(0, var(--size) - 2) * (1 - var(--fetch2))))',
        'access': choose('opcode', {k: v['access'] for k, v in ops.items() if 'access' in v}, 0),
        'word': choose('opcode', {k: v['word'] for k, v in ops.items() if 'word' in v}, 0),
        'writing': choose('opcode', {k: v.get('writing', 'var(--access)') for k, v in ops.items() if 'write' in v}, 0),
        'write': choose('opcode', {k: v['write'] for k, v in ops.items() if 'write' in v}, 0),
        'write2': choose('opcode', {k: v['write2'] for k, v in ops.items() if 'write2' in v}, 0),
        'writable': choose('address', {i: 1 for i in MEMORY}, 0),
        'readable': rom.readable('address', choose, MEMORY),
        'valid': 'calc(var(--writing) * var(--writable) + (1 - var(--writing)) * var(--readable))',
        'read': rom.lookup('address', choose, read_memory, 'var(--readable)'),
        'writable2': choose('address2', {i: 1 for i in MEMORY}, 0),
        'readable2': rom.readable('address2', choose, MEMORY),
        'valid2': 'calc(var(--writing) * var(--writable2) + (1 - var(--writing)) * var(--readable2))',
        'read2': rom.lookup('address2', choose, read_memory, 'var(--readable2)'),
    }
    immediates = (0xC6,0xCE,0xD6,0xDE,0xE6,0xEE,0xF6,0xFE)
    operand = choose('alu-index', {i: f'var(--{reg})' if reg else 'var(--read)' for i, reg in enumerate(REGS)}, 0)
    logic = {}
    for kind, combine in [(4,lambda a,b: f'min({a}, {b})'),
                          (5,lambda a,b: f'abs(({a}) - ({b}))'),
                          (6,lambda a,b: f'max({a}, {b})')]:
        terms = []
        for bit in range(8):
            a = f'mod(round(down, var(--a) / {1 << bit}), 2)'
            b = f'mod(round(down, var(--alu-input) / {1 << bit}), 2)'
            terms.append(f'({combine(a,b)}) * {1 << bit}')
        logic[kind] = 'calc(' + ' + '.join(terms) + ')'
    half_add = 'round(down, (mod(var(--a),16) + mod(var(--alu-input),16) + var(--alu-cin)) / 16)'
    half_sub = 'max(0, sign(mod(var(--alu-input),16) + var(--alu-cin) - mod(var(--a),16)))'
    arithmetic_flags = f'calc({zero("var(--alu-result)")} + var(--alu-sub) * 64 + ((1 - var(--alu-sub)) * ({half_add}) + var(--alu-sub) * ({half_sub})) * 32 + ((1 - var(--alu-sub)) * round(down, var(--alu-wide) / 256) + var(--alu-sub) * max(0, sign(0 - var(--alu-wide)))) * 16)'
    expr.update({
        'cb-index': 'calc(mod(var(--imm), 8))',
        'cb-group': 'calc(round(down, var(--imm) / 64))',
        'cb-kind': 'calc(mod(round(down, var(--imm) / 8), 8))',
        'cb-input': choose('cb-index', {i: f'var(--{reg})' if reg else 'var(--read)' for i, reg in enumerate(REGS)}, 0),
        'cb-weight': choose('cb-kind', {i: 1 << i for i in range(8)}, 1),
        'cb-bit': 'calc(mod(round(down, var(--cb-input) / var(--cb-weight)), 2))',
        'cb-mutate': f'calc(1 - ({equals("cb-group", 1)}))',
        'cb-rotate': choose('cb-kind', {
            0: 'calc(mod(var(--cb-input) * 2, 256) + round(down, var(--cb-input) / 128))',
            1: 'calc(round(down, var(--cb-input) / 2) + mod(var(--cb-input), 2) * 128)',
            2: 'calc(mod(var(--cb-input) * 2, 256) + var(--carry))',
            3: 'calc(round(down, var(--cb-input) / 2) + var(--carry) * 128)',
            4: 'calc(mod(var(--cb-input) * 2, 256))',
            5: 'calc(round(down, var(--cb-input) / 2) + round(down, var(--cb-input) / 128) * 128)',
            6: 'calc(mod(var(--cb-input), 16) * 16 + round(down, var(--cb-input) / 16))',
            7: 'calc(round(down, var(--cb-input) / 2))'}, 0),
        'cb-carry': choose('cb-kind', {i: 'calc(round(down, var(--cb-input) / 128))' for i in (0,2,4)} |
                           {i: 'calc(mod(var(--cb-input), 2))' for i in (1,3,5,7)}, 0),
        'cb-result': choose('cb-group', {0: 'var(--cb-rotate)',
            2: 'calc(var(--cb-input) - var(--cb-bit) * var(--cb-weight))',
            3: 'calc(var(--cb-input) + (1 - var(--cb-bit)) * var(--cb-weight))'}, 'var(--cb-input)'),
        'cb-flags': choose('cb-group', {0: f'calc({zero("var(--cb-result)")} + var(--cb-carry) * 16)',
            1: 'calc((1 - var(--cb-bit)) * 128 + 32 + var(--carry) * 16)'}, 'var(--f)'),
        'alu-index': 'calc(mod(var(--opcode), 8))',
        'alu-op': choose('opcode', {code: i for i, code in enumerate(immediates)}, 'calc(mod(round(down, var(--opcode) / 8), 8))'),
        'alu-input': choose('opcode', {code: 'var(--imm)' for code in immediates}, operand),
        'alu-cin': choose('alu-op', {1: 'var(--carry)', 3: 'var(--carry)'}, 0),
        'alu-sub': 'calc(min(1, max(0, var(--alu-op) - 1)))',
        'alu-wide': 'calc(var(--a) + (1 - 2 * var(--alu-sub)) * (var(--alu-input) + var(--alu-cin)))',
        'alu-result': choose('alu-op', logic, 'calc(mod(var(--alu-wide), 256))'),
        'alu-flags': choose('alu-op', {i: f'calc({zero("var(--alu-result)")} + {32 if i == 4 else 0})' for i in (4,5,6)}, arithmetic_flags),
        'subtract': 'calc(mod(round(down, var(--f) / 64), 2))',
        'half-carry': 'calc(mod(round(down, var(--f) / 32), 2))',
        'daa-high': 'calc(max(var(--carry), (1 - var(--subtract)) * max(0, sign(var(--a) - 153))))',
        'daa-low': 'calc(max(var(--half-carry), (1 - var(--subtract)) * max(0, sign(mod(var(--a),16) - 9))))',
        'daa-result': 'calc(mod(var(--a) + (1 - 2 * var(--subtract)) * (var(--daa-high) * 96 + var(--daa-low) * 6), 256))',
    })
    for lane, (name, pc) in enumerate([('raw-opcode', 'pc'), ('imm', 'pc1'), ('upper', 'pc2')]):
        expr[f'fetch{lane}'] = rom.readable(pc, choose, MEMORY)
        expr[name] = rom.lookup(pc, choose, {i: f'var(--m{i})' for i in MEMORY}, f'var(--fetch{lane})')
    # FF is now RST 38: an unmapped byte must not turn into a synthetic call.
    expr['invalid'] = 'calc(max(1 - var(--known), (1 - var(--irq)) * (1 - var(--fetch-valid)), var(--access) * max(1 - var(--valid), var(--word) * (1 - var(--valid2)))))'
    expr['enabled'] = 'calc(var(--run, 1) * (1 - max(var(--sleeping), var(--fault), var(--invalid))))'
    for lane in ('write','write2'):
        expr[lane] = expr[lane].replace('var(--pc)', 'var(--exec-pc)')
    expr.update(timer_expr)
    expr.update(serial_expr)
    acknowledged = f'(var(--m{IF}) - var(--enabled) * var(--irq) * var(--irq-mask))'
    expr['timer-if'] = f'calc({acknowledged} + var(--timer-request6) * (1 - mod(round(down,{acknowledged} / 4),2)) * 4)'
    expr['hardware-if'] = 'calc(var(--timer-if) + 8 * var(--serial-done) * (1 - mod(round(down,var(--timer-if) / 8),2)))'
    css += '\n.machine {' + ''.join(f'--{k}:{v};' for k, v in expr.items()) + '}\n'
    states = {}
    stopped = 'style(--sleeping:1) or style(--fault:1)'
    invalid = 'style(--invalid:1)'
    for name in ['pc', 'a', 'b', 'c', 'd', 'e', 'h', 'l', 'f', 'sp', 'halted', 'fault', 'ticks', 'tcycles', 'ime', 'ime-delay', 'halt-bug']:
        initial = 256 if name == 'pc' else 0
        default = f'var(--{name})'
        if name in ('halted', 'halt-bug', 'ime-delay'): default = '0'
        if name == 'ime': default = 'calc(max(var(--ime), var(--ime-delay)))'
        if name == 'ticks': default = 'calc(var(--ticks) + 1)'
        if name == 'tcycles': default = 'calc(mod(var(--tcycles) + var(--duration), 65536))'
        changes = {}
        for code, effects in ops.items():
            if name == 'pc':
                changes[code] = effects.get('pc', f'calc(mod(var(--pc) + {effects["size"]}, 65536))')
            elif name in effects: changes[code] = effects[name]
        calc = choose('opcode', changes, default) if changes else default
        # HALT bug suppresses one opcode-fetch PC increment, including CALL/RST
        # return addresses and relative jumps; the opcode itself still uses PC.
        calc = calc.replace('var(--pc)', 'var(--exec-pc)') if name == 'pc' else calc
        on_invalid = '1' if name == 'fault' else f'var(--{name})'
        result = f'if({stopped}:var(--{name});{invalid}:{on_invalid};style(--enabled:1):{calc};else:var(--{name}))'
        if arithmetic:
            result = f'calc(var(--{name}) + var(--enabled) * (({calc}) - var(--{name})))'
            if name == 'fault':
                result = 'calc(max(var(--fault), var(--run, 1) * (1 - var(--sleeping)) * var(--invalid)))'
        states[name] = (initial, result)
    for addr in MEMORY:
        if addr in (DIV,TIMA,TMA,TAC,SB,SC): continue
        name = f'm{addr}'
        result = f'if(style(--enabled:1) and style(--writing:1) and style(--address:{addr}):var(--write);style(--enabled:1) and style(--writing:1) and style(--word:1) and style(--address2:{addr}):var(--write2);else:var(--{name}))'
        if arithmetic:
            result = f'calc(var(--{name}) + var(--enabled) * var(--writing) * (({equals("address", addr)}) * (var(--write) - var(--{name})) + var(--word) * ({equals("address2", addr)}) * (var(--write2) - var(--{name}))))'
        if addr == IF:
            # Acknowledge before stack writes; an explicit IF write wins.
            result = result.replace(f'var(--{name})', 'var(--hardware-if)')
            result = f'calc(224 + mod(({result}),32))'
        states[name] = (224 if addr == IF else 0, result)
    states.update(timer_states)
    states.update(serial_states)
    css += storage(states)
    pending = ' + '.join(f'mod(round(down,var(--m{IF}) / {1<<bit}),2) * mod(round(down,var(--m{IE}) / {1<<bit}),2)' for bit in range(5))
    css += '\n.machine{--resume:calc(min(1,' + pending + f' + mod(round(down,var(--m{TAC}) / 4),2) + var(--timer-reload) + round(down,var(--m{SC}) / 128) * mod(var(--m{SC}),2)));}}\n'
    for name in ['pc', 'a', 'b', 'f', 'sp', 'ticks', 'tcycles', *[f'm{i}' for i in (DIV,TIMA,TMA,TAC,SB,SC)]]:
        css += f'.register-{name}::after {{counter-reset:value var(--{name});content:counter(value);}}\n'
    for pair in ('bc', 'de', 'hl'):
        css += f'.register-{pair}::after {{counter-reset:value calc(var(--{pair[0]}) * 256 + var(--{pair[1]}));content:counter(value);}}\n'
    css += '''
@container style(--halted:1) {.running-message{display:none}.halt-message{display:block}}
@container style(--fault:1) {.running-message{display:none}.fault-message{display:block}}
@container style(--m49154:165) {.halt-message .passed{display:inline-block}.halt-message .stopped{display:none}}
@container style(--halted:1) and style(--resume:1) {.halt-message{display:none}.timer-message{display:block}}
'''
    return css + monitor_css()


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
