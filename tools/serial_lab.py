"""Original serial diagnostic ROM assembly; CPU execution stays in CSS."""
from rom import ROM


def serial_rom():
    data=bytearray(32768)
    data[0x100:0x103]=bytes([0xC3,0x50,1])
    data[0x58:0x5A]=bytes([0x04,0xD9])  # Count serial IRQs, then RETI.
    code,checks=[],[]
    def emit(*values):code.extend(values)
    def check():emit(0xC2,0,0);checks.append(len(code)-2)
    emit(0x31,0xFE,0xFF,0xF3,0xAF,0xE0,15,0x3E,8,0xE0,255)
    emit(0x3E,ord('O'),0xE0,1,0x3E,0x81,0xE0,2,0xFB,0,0x76)
    emit(0x78,0xFE,1);check()
    emit(0xF0,1,0xFE,255);check()
    emit(0xF0,2,0xFE,127);check()
    emit(0x3E,ord('K'),0xE0,1,0x3E,0x81,0xE0,2)
    emit(0xF0,2,0xE6,0x80,0x20,0xFA)  # Poll the actual completion bit.
    emit(0x78,0xFE,2);check()
    emit(0x3E,0xA5,0xEA,2,0xC0,0x76)
    failure=0x150+len(code)
    emit(0xAF,0xE0,2,0x3E,0xFF,0xEA,2,0xC0,0x76)
    for index in checks:code[index:index+2]=[failure%256,failure//256]
    data[0x150:0x150+len(code)]=bytes(code)
    return ROM(data,base=0)


def boundary_rom():
    data=bytearray(0x100)
    data[0x58:0x5A]=bytes([0x04,0xD9])
    data.extend([0x3E,0xA5,0xEA,2,0xC0,0x76])
    return ROM(data,base=0)


def boundary_seed():
    return {'sp':65534,'ime':1,'halted':1,'m65535':8,'m65281':255,'m65282':255,
            'serial-bits':7,'serial-tx':32,'serial-count':65535,'serial-length':16,
            **{f'serial-log{i}':c for i,c in enumerate(b'0123456789ABCDEF')}}
