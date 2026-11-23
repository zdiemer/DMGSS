"""ROM address lookup generation. Bytes are encoded, never executed here."""
from collections import Counter


class ROM:
    def __init__(self, data, base=0x100, compact=True):
        self.compact = compact
        self.data = bytes(data)
        self.base = base
        self.end = base + len(self.data)
        self.fill = Counter(self.data).most_common(1)[0][0] if self.data else 255
        self.exceptions = {base + i: b for i, b in enumerate(self.data) if not compact or b != self.fill}

    def contains(self, key):
        if not self.data:
            return '0'
        return f'max(0, min(1, var(--{key}) - {self.base} + 1, {self.end} - var(--{key})))'

    def readable(self, key, choose, addresses):
        ram = {address: 1 for address in addresses}
        if not self.compact:
            return choose(key, {**{address: 1 for address in self.exceptions}, **ram}, 0)
        return f'calc({self.contains(key)} + ({choose(key, ram, 0)}))'

    def lookup(self, key, choose, extra=None, valid=None):
        table = {**self.exceptions, **(extra or {})}
        if not self.compact:
            # Preserve the small embedded cartridges' original lookup graph.
            # Avoid new range dependencies in the already timing-sensitive
            # automatic pipeline when a large address range is not needed.
            return choose(key, table, 255)
        selected = choose(key, table, self.fill)
        # Padding is still mapped ROM, including zero bytes. Out-of-range fetch
        # is rejected by the CPU fetch-validity gate (FF itself is valid RST).
        return f'calc(255 + ({valid or self.contains(key)}) * (({selected}) - 255))'
