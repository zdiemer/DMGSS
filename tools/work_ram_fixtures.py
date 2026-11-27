"""Original full-map retention fixtures. Encode bytes and seeds, never execute."""


def build(build_automatic, root):
    initial = {f'm{0xC000+i}': (i*73+(i>>8)*19+11)&255 for i in range(8192)}
    code = []
    for page in range(32):
        # Cross a packed-word boundary on each page; include both echo banks
        # and the physical DE/DF pages that have no echo aliases.
        high = 0xE0+page if page < 30 else 0xC0+page
        code.extend([0x31,page+17,page+1,0x08,0x7F,high])
    code.extend([0]*64 + [0xFA,0x7F,0xE0,0x47,0xFA,0x80,0xDF,0x4F,0x76])
    build_automatic(code, root/'all-bytes', initial=initial)
    for seed in (0,0x3412):
        code = []
        for value, address in [(0xFFFF,0xC000),(seed,0xE000)]:
            code.extend([0x31,value&255,value>>8,0x08,address&255,address>>8]+[0]*126)
        code.extend([0]*128)
        code.extend([0x31,0xCD,0xAB,0x08,0,0xC0]+[0]*126)
        code.extend([0xFA,0,0xE0,0x47,0xFA,1,0xE0,0x76])
        build_automatic(code,root/f'reactivate-{seed}',initial={'m49152':seed&255,'m49153':seed>>8})


def fallback_code():
    """Cross physical/echo pages and both ends without native conditionals."""
    return [0x31,0x34,0x12,0x08,0xFF,0xC0,
            0x31,0x78,0x56,0x08,0xFF,0xEF,
            0x31,0xBC,0x9A,0x08,0xFF,0xDF,
            0x31,0xF0,0xDE,0x08,0xFE,0xFD,
            0xFA,0,0xF0,0x21,0xFF,0xFD,0x2A,0x76]
