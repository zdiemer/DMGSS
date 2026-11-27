"""Original work/echo RAM diagnostic. Assemble bytes, never execute them."""


def sample_rom():
    data = bytearray(32768)
    data[0x100:0x103] = bytes([0xC3,0x50,1])
    data[0x134:0x13D] = b'DMGSS RAM'
    code, checks = [], []
    # Both directions, including newly mapped bytes and the last physical byte.
    for write, read, value in [(0xC000,0xE000,0x12),(0xEFFF,0xCFFF,0x34),
                               (0xD000,0xF000,0x56),(0xDFFF,0xDFFF,0x78)]:
        code.extend([0x3E,value,0xEA,write&255,write>>8,0xFA,read&255,read>>8,0xFE,value,0xC2,0,0])
        checks.append(len(code)-2)
    code.extend([0x3E,0xA5,0xEA,2,0xC0,0x76])
    fail = 0x150 + len(code)
    code.extend([0x3E,0xFF,0xEA,2,0xC0,0x76])
    for index in checks:
        code[index:index+2] = [fail&255,fail>>8]
    data[0x150:0x150+len(code)] = bytes(code)
    data[0x14D] = (-sum(data[0x134:0x14D])-25)&255
    data[0x14E:0x150] = (sum(data)&65535).to_bytes(2,'big')
    return bytes(data)
