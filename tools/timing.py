"""SM83 instruction durations; emit CSS, never execute instructions in Python.

Units in the table are M-cycles (four DMG T-cycles). Conditional entries are
the untaken duration. Bus ordering, HALT idle time and peripherals are separate.
Reference: https://gbdev.io/gb-opcodes/optables/
"""

BASE = [
    1,3,2,2,1,1,2,1,5,2,2,2,1,1,2,1,
    0,3,2,2,1,1,2,1,3,2,2,2,1,1,2,1,
    2,3,2,2,1,1,2,1,2,2,2,2,1,1,2,1,
    2,3,2,2,3,3,3,1,2,2,2,2,1,1,2,1,
    *[2 if destination == 6 or source == 6 else 1
      for destination in range(8) for source in range(8)],
    *[2 if source == 6 else 1 for _ in range(8) for source in range(8)],
    2,3,3,4,3,4,2,4,2,4,3,0,3,6,2,4,
    2,3,3,0,3,4,2,4,2,4,3,0,3,0,2,4,
    3,3,2,0,0,4,2,4,4,1,4,0,0,0,2,4,
    3,3,2,1,0,4,2,4,3,2,4,1,0,0,2,4,
]
BASE[0x76] = 1  # HALT entry only, not time spent asleep.


def duration(choose):
    values = {code: 4 * cycles for code, cycles in enumerate(BASE) if cycles}
    conditions = ['1 - var(--z)', 'var(--z)', '1 - var(--carry)', 'var(--carry)']
    for codes, extra in [((0x20,0x28,0x30,0x38),1),
                         ((0xC2,0xCA,0xD2,0xDA),1),
                         ((0xC4,0xCC,0xD4,0xDC),3),
                         ((0xC0,0xC8,0xD0,0xD8),3)]:
        for code, condition in zip(codes, conditions):
            values[code] = f'calc({4 * BASE[code]} + {4 * extra} * ({condition}))'
    # CB register: 2 M; BIT [HL]: 3 M; modifying [HL]: 4 M.
    values[0xCB] = 'calc(8 + max(0,1 - abs(var(--cb-index) - 6)) * (4 + 4 * var(--cb-mutate)))'
    values[256] = 20  # Interrupt entry, with no retired instruction tick.
    return choose('opcode', values, 0)
