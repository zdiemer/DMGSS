"""Physical DMG work RAM encoded as exact 16-bit words, never executed here."""
START, END = 0xC000, 0xE000
WORDS = range(START, END, 2)


def pack_initial(initial):
    """Keep fixture/import initialization byte-oriented at the public boundary."""
    initial = initial or {}
    result = {k:v for k,v in initial.items() if not (k.startswith('m') and k[1:].isdigit() and START <= int(k[1:]) < END)}
    for address in WORDS:
        if f'm{address}' in initial or f'm{address+1}' in initial:
            result[f'wram{address}'] = initial.get(f'm{address}',0) + 256*initial.get(f'm{address+1}',0)
    return result


def views():
    """Decode the two console signals; test observers decode other words directly."""
    rules, values = [], []
    for address in (START,START+2):
        # Only the two console signals need to propagate into UI descendants.
        rules.append(f'@property --m{address} {{syntax:"<integer>";inherits:true;initial-value:0;}}')
        values.append(f'--m{address}:mod(round(down,var(--wram{address & ~1}) / {256**(address%2)}),256);')
    return '\n'.join(rules) + '\n.machine,.result {' + ''.join(values) + '}\n'
