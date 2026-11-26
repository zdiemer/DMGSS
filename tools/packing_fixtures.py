"""Original programs for automatic RAM storage checks; no CPU execution."""


def build(builder, out):
    for seed, target in [(0,65535),(65535,0),(65280,255),(255,65280)]:
        # First batch writes a whole word and the unpaired HRAM/IE endpoints.
        first = [0x31,target&255,target>>8,0x08,0,0xC0,
                 0x3E,0xA5,0xEA,0xFE,0xFF,0x3E,0xC0,0xE0,0xFF] + [0]*122
        # Second batch reads both bytes, changes the low byte through echo,
        # verifies its neighbour, then changes only the high byte.
        second = [0xFA,0,0xC0,0x47,0xFA,1,0xC0,0x4F,0x21,0,0xE0,0x34,
                  0xFA,0,0xC0,0x57,0xFA,1,0xC0,0x5F,0x3E,0x42,0xEA,1,0xE0] + [0]*116
        third = [0xFA,0,0xC0,0x67,0xFA,1,0xC0,0x76]
        initial = {'m49152':seed&255,'m49153':seed>>8,
                   'm65532':0xAB,'m65533':0xCD,'m65534':0x5A,'m65535':0xA0}
        builder(first+second+third,out/f'lanes-{seed}',initial=initial)
    for seed, target in [(0,65535),(1,0)]:
        # Both cases require the maximum scroll offset, including wrapped seeds.
        code = [0x31,target&255,target>>8,0x08,0,0xC0] + [0]*126
        code += [0xFA,0,0xC0,0x47,0xFA,1,0xC0,0x4F,0x76]
        builder(code,out/f'max-{seed}',initial={'m49152':seed&255,'m49153':seed>>8})
