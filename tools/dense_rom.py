"""Original dense ROM data and diagnostic. Encoding only; never executes code."""


def dense_data(size=32768):
    return bytearray(((i * 73) ^ ((i >> 5) * 29) ^ ((i * i) >> 9)) & 255 for i in range(size))


def sample_rom():
    data = dense_data()
    data[0x100:0x104] = bytes([0xC3, 0x50, 1, 0])
    data[0x104:0x150] = bytes(0x4C)  # Original cartridge: no Nintendo logo.
    data[0x134:0x13F] = b'DMGSS DENSE'
    locations = [(0,0), (0xFF,255), (0x200,128), (0x1FFF,1), (0x2000,254),
                 (0x3FFF,85), (0x4000,170), (0x7FFE,127), (0x7FFF,42)]
    code, failures = [], []
    for address, value in locations:
        data[address] = value
        code.extend([0xFA, address & 255, address >> 8, 0xFE, value, 0x20, 0])
        failures.append(len(code)-1)
    code.extend([0x3E,0xA5,0xEA,2,0xC0,0x76])
    fail = len(code)
    code.extend([0x3E,0xFF,0xEA,2,0xC0,0x76])
    for index in failures:
        code[index] = fail-index-1
    data[0x150:0x150+len(code)] = bytes(code)
    data[0x14D] = (-sum(data[0x134:0x14D])-25) & 255
    data[0x14E:0x150] = ((sum(data[:0x14E])+sum(data[0x150:])) & 65535).to_bytes(2,'big')
    return bytes(data)
