"""Physical DMG work/video RAM encoded as exact 16-bit words, never executed here."""
START, END = 0xC000, 0xE000
WORDS = range(START, END, 2)
VIDEO_START, VIDEO_END = 0x8000, 0xA000
VIDEO_WORDS = range(VIDEO_START, VIDEO_END, 2)


def packed(address):
    return START <= address < END or VIDEO_START <= address < VIDEO_END


def word_name(address):
    return f'{"vram" if VIDEO_START <= address < VIDEO_END else "wram"}{address & ~1}'


def pack_initial(initial):
    """Keep fixture/import initialization byte-oriented at the public boundary."""
    initial = initial or {}
    result = {k:v for k,v in initial.items() if not (k.startswith('m') and k[1:].isdigit() and packed(int(k[1:])))}
    for address in (*VIDEO_WORDS, *WORDS):
        if f'm{address}' in initial or f'm{address+1}' in initial:
            result[word_name(address)] = initial.get(f'm{address}',0) + 256*initial.get(f'm{address+1}',0)
    return result


def views():
    """Decode only visible tile/console bytes; observers decode other words directly."""
    rules, values = [], []
    for address in (*range(VIDEO_START,VIDEO_START+16),START,START+2):
        # Only visible bytes need to propagate into UI descendants.
        rules.append(f'@property --m{address} {{syntax:"<integer>";inherits:true;initial-value:0;}}')
        values.append(f'--m{address}:mod(round(down,var(--{word_name(address)}) / {256**(address%2)}),256);')
    return '\n'.join(rules) + '\n.machine,.result {' + ''.join(values) + '}\n'
