"""Original interrupt diagnostics: assemble bytes only; execution stays in CSS."""
from rom import ROM


def interrupt_rom():
    data = bytearray(32768)
    data[0x100:0x103] = bytes([0xC3,0x50,1])
    for i in range(5):
        # Record service order through the old-state HL pointer, then RETI.
        data[0x40+8*i:0x44+8*i] = bytes([0x3E,i+1,0x22,0xD9])
    code, checks = [], []
    def emit(*values): code.extend(values)
    def check():
        emit(0xC2,0,0)
        checks.append(len(code)-2)
    emit(0x31,0xFE,0xFF,0x21,0x10,0xC0,0x3E,31,0xE0,0xFF,0xE0,0x0F,0xFB,0)
    emit(0x21,0x10,0xC0)
    for value in range(1,6):
        emit(0x2A,0xFE,value); check()
    emit(0xF0,0x0F,0xFE,0xE0); check()
    # With IME off and a request pending, HALT duplicates the following INC B.
    emit(0xF3,0x3E,1,0xE0,0x0F,0x76,0x04,0x78,0xFE,2); check()
    emit(0xAF,0xE0,0x0F,0x3E,0xA5,0xEA,2,0xC0,0x76)
    failure = 0x150+len(code)
    emit(0xAF,0xE0,0x0F,0x3E,0xFF,0xEA,2,0xC0,0x76)
    for index in checks:code[index:index+2]=[failure%256,failure//256]
    data[0x150:0x150+len(code)] = bytes(code)
    return ROM(data,base=0)


def interrupt_continuation(kind):
    data = bytearray(0x100)
    data[0x40:0x42] = bytes([0x04,0xD9])
    setup = [0x31,0xFE,0xFF,0x3E,1,0xE0,0xFF,0xE0,0x0F]
    if kind == 'delay':
        # EI occupies stage 128. Its delayed enable must survive copying.
        code = setup+[0]*123+[0xFB,0,0x76]
    elif kind == 'service':
        # Stage 128 is interrupt entry, carrying a live frame and cleared IME.
        code = setup+[0]*121+[0xFB,0,0x76]
    elif kind == 'bug':
        # HALT occupies stage 128; the duplicated fetch is in the next bank.
        code = setup+[0]*123+[0x76,0x04,0xAF,0xE0,0x0F,0x76]
    else:
        raise ValueError(kind)
    data.extend(code)
    return ROM(data,base=0)
