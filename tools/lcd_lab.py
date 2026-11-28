"""Original ROM assembly for LCD waits. Never execute the generated program."""
from rom import ROM


def lcd_rom():
    data = bytearray(0x100)
    # STAT handler records LY, disables the LCD so the final HALT is quiescent.
    data[0x48:0x51] = bytes([0xF0,0x44,0x47,0xAF,0xE0,0x40,0x04,0xD9,0])
    # Wait for LYC=2. At least two complete 128-stage batches are needed.
    data.extend([0x31,0xFE,0xFF,0xF3,0xAF,0xE0,0x0F,
                 0x3E,2,0xE0,0x45,0xE0,0xFF,
                 0x3E,0x40,0xE0,0x41,0x3E,0x80,0xE0,0x40,
                 0xFB,0,0x76,0x78,0xFE,3,0x20,7,
                 0x3E,0xA5,0xEA,2,0xC0,0x76,0xD3,
                 0x3E,0xFF,0xEA,2,0xC0,0x76])
    return ROM(data,base=0)


def boundary_rom():
    data = bytearray(0x100)
    # Both hardware sources can wake this fixture. Count dispatch, stop LCD.
    for vector in (0x40,0x48):
        data[vector:vector+6] = bytes([0x04,0xAF,0xE0,0x40,0xD9,0])
    data.extend([0x3E,0xA5,0xEA,2,0xC0,0x76])
    return ROM(data,base=0)


def boundary_seed():
    # A bank ends exactly at line 143 dot 452; the next stage enters VBlank.
    return {'sp':65534,'ime':1,'halted':1,'m65535':1,'m65344':128,
            'm65345':128,'m65348':142,'m65349':255,
            'lcd-line':142,'lcd-dot':396}


def blocked_rom():
    # Raise STAT during VBlank, explicitly clear IF while its signal stays high,
    # then HALT. Retaining the high signal must prevent another request.
    return ROM([0x3E,16,0xE0,0x41,0xAF,0xE0,0x0F,0x76])


def blocked_seed():
    return {'halted':0,'m65535':2,'m65344':128,'m65345':129,
            'm65348':144,'m65349':255,'lcd-line':144}
