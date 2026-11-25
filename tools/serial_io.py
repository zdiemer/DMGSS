"""Disconnected DMG serial circuitry and a bounded diagnostic monitor.

Only emit CSS; never execute a ROM. Internal transfers use 512 T-cycles per
bit, with a fresh phase on each SC write. This is not DIV/serial phase or
mid-M-cycle bus-race emulation. External clocks have no attached source.
"""
SB, SC = 0xFF01, 0xFF02
LOG_SIZE = 16


def circuit(equals):
    expr = {
        'serial-live': f'calc(round(down,var(--m{SC}) / 128) * mod(var(--m{SC}),2))',
        'serial-elapsed': 'calc(var(--serial-phase) + var(--serial-live) * var(--timer-cycles))',
        # An accepted CPU operation is at most 24 T-cycles: at most one bit edge.
        'serial-edge': 'calc(var(--serial-live) * round(down,var(--serial-elapsed) / 512))',
        'serial-done': f'calc(var(--serial-edge) * ({equals("serial-bits",7)}))',
        'serial-sb': f'calc(var(--m{SB}) + var(--serial-edge) * (mod(2 * var(--m{SB}) + 1,256) - var(--m{SB})))',
        'serial-sc': f'calc(var(--m{SC}) - 128 * var(--serial-done))',
        'serial-sent': f'calc(var(--serial-tx) + var(--serial-edge) * (mod(2 * var(--serial-tx) + round(down,var(--m{SB}) / 128),256) - var(--serial-tx)))',
    }
    for addr in (SB, SC):
        expr[f'io-hit{addr}'] = f'calc(var(--enabled) * var(--writing) * (({equals("address",addr)}) + var(--word) * ({equals("address2",addr)})))'
        expr[f'io-data{addr}'] = f'calc(({equals("address",addr)}) * var(--write) + var(--word) * ({equals("address2",addr)}) * var(--write2))'
    # All explicit CPU writes happen after the clocked read/completion boundary.
    states = {
        f'm{SB}': (0,f'calc(var(--serial-sb) + var(--io-hit{SB}) * (var(--io-data{SB}) - var(--serial-sb)))'),
        f'm{SC}': (126,f'calc(var(--serial-sc) + var(--io-hit{SC}) * (126 + mod(var(--io-data{SC}),2) + 128 * round(down,var(--io-data{SC}) / 128) - var(--serial-sc)))'),
        'serial-phase': (0,f'calc((1 - max(var(--io-hit{SC}),var(--serial-done))) * mod(var(--serial-elapsed),512))'),
        'serial-bits': (0,f'calc((1 - var(--io-hit{SC})) * mod(var(--serial-bits) + var(--serial-edge),8))'),
        'serial-tx': (0,f'calc((1 - var(--io-hit{SC})) * var(--serial-sent))'),
        'serial-count': (0,'calc(mod(var(--serial-count) + var(--serial-done),65536))'),
        'serial-length': (0,f'calc(min({LOG_SIZE},var(--serial-length) + var(--serial-done)))'),
    }
    full=equals('serial-length',LOG_SIZE)
    for i in range(LOG_SIZE):
        old=f'var(--serial-log{i})'
        shifted=f'var(--serial-log{i+1})' if i+1<LOG_SIZE else 'var(--serial-sent)'
        states[f'serial-log{i}']=(0,f'calc({old} + var(--serial-done) * ((1 - ({full})) * ({equals("serial-length",i)}) * (var(--serial-sent) - {old}) + ({full}) * ({shifted} - {old})))')
    return expr, states


def monitor_css():
    symbols=[]
    for i in range(256):
        c=chr(i) if 32<=i<=126 else {9:'⇥',10:'↵',13:'␍'}.get(i,'·')
        symbols.append('"'+c.replace('\\','\\\\').replace('"','\\"')+'"')
    css='@counter-style serial-text{system:fixed 0;symbols:'+ ' '.join(symbols)+';suffix:""}\n'
    css+='@counter-style serial-hex{system:numeric;symbols:"0" "1" "2" "3" "4" "5" "6" "7" "8" "9" "A" "B" "C" "D" "E" "F";pad:2 "0";suffix:""}\n'
    css+='.serial-count::after{counter-reset:n var(--serial-count);content:counter(n)}\n'
    for i in range(LOG_SIZE):
        css+=f'.serial-byte{i}::after{{counter-reset:n var(--serial-log{i});content:counter(n,serial-text)}}\n.serial-hex .serial-byte{i}::after{{content:counter(n,serial-hex)}}\n'
    for length in range(LOG_SIZE+1):
        css+=f'@container style(--serial-length:{length}){{.serial-bytes span:nth-child(n+{length+1}){{display:none}}}}\n'
    return css


def monitor_html():
    cells=''.join(f'<span class="serial-byte{i}"></span>' for i in range(LOG_SIZE))
    return ('<details class="serial-monitor"><summary>Serial output</summary>'
            '<p>Last 16 completed bytes · oldest first</p>'
            f'<samp class="serial-bytes serial-text" aria-label="Serial text">{cells}</samp>'
            f'<samp class="serial-bytes serial-hex" aria-label="Serial hexadecimal bytes">{cells}</samp>'
            '<p><span class="serial-count"></span> bytes sent (count wraps at 65,536). '
            'Control bytes appear as marks; exact bytes are shown in hex. '
            'Disconnected link: receives FF. No external clock or cable peer.</p></details>')
