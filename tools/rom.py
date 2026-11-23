"""ROM address lookup generation. Bytes are encoded, never executed here."""
from collections import Counter


class ROM:
    def __init__(self, data, base=0x100):
        self.data = bytes(data)
        self.base = base
        self.end = base + len(self.data)
        self.fill = Counter(self.data).most_common(1)[0][0] if self.data else 255
        self.exceptions = {base + i: b for i, b in enumerate(self.data) if b != self.fill}

    def contains(self, key):
        if not self.data:
            return '0'
        return f'max(0, min(1, var(--{key}) - {self.base} + 1, {self.end} - var(--{key})))'

    def lookup(self, key, choose, extra=None, valid=None):
        table = {**self.exceptions, **(extra or {})}
        selected = choose(key, table, self.fill)
        # Padding is still mapped ROM, including zero bytes. Out-of-range fetch
        # retains the decoder's explicit 255/unknown-opcode trap behavior.
        return f'calc(255 + ({valid or self.contains(key)}) * (({selected}) - 255))'
