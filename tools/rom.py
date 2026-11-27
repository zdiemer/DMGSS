"""ROM address lookup generation. Bytes are encoded, never executed here."""
from collections import Counter

DIRECT_LIMIT = 1024


class ROM:
    def __init__(self, data, base=0x100, compact=True, mbc1=False):
        self.mbc1 = mbc1
        self.compact = compact
        self.data = bytes(data)
        self.base = base
        self.end = base + len(self.data)
        self.fill = Counter(self.data).most_common(1)[0][0] if self.data else 255
        self.exceptions = {base + i: b for i, b in enumerate(self.data) if not compact or b != self.fill}
        self.lookup_expr = {}

    @property
    def paged(self):
        return self.compact and len(self.exceptions) > DIRECT_LIMIT

    def paged_lookup(self, key, choose):
        """Pure byte encoding: 256-byte pages, with exact 16-bit packed pairs.

        Registered intermediate values bound each selector expression. Identical
        pages share a selector, and each page has its own most-common pair.
        Neither packing nor deduplication depends on reachable instructions.
        """
        prefix = f'rom-{key}'
        expr = self.lookup_expr
        expr[f'{prefix}-page'] = f'calc(round(down,var(--{key}) / 256))'
        expr[f'{prefix}-word'] = f'calc(round(down,mod(var(--{key}),256) / 2))'
        pages, unique = {}, {}
        def at(address):
            return self.data[address-self.base] if self.base <= address < self.end else 255
        for page in range(self.base // 256, (self.end + 255) // 256):
            pairs = tuple(at(page*256+i) + 256*at(page*256+i+1) for i in range(0,256,2))
            if pairs not in unique:
                name = f'{prefix}-row{len(unique)}'
                fill = Counter(pairs).most_common(1)[0][0]
                differences = {i:v for i,v in enumerate(pairs) if v != fill}
                expr[name] = choose(f'{prefix}-word', differences, fill) if differences else str(fill)
                unique[pairs] = name
            pages[page] = f'var(--{unique[pairs]})'
        expr[f'{prefix}-packed'] = choose(f'{prefix}-page', pages, 65535)
        expr[f'{prefix}-byte'] = f'calc(mod(round(down,var(--{prefix}-packed) / (1 + 255 * mod(var(--{key}),2))),256))'
        return f'var(--{prefix}-byte)'

    def contains(self, key):
        if not self.data:
            return '0'
        end = 32768 if self.mbc1 else self.end
        return f'max(0, min(1, var(--{key}) - {self.base} + 1, {end} - var(--{key})))'

    def readable(self, key, choose, addresses):
        ram = {address: 1 for address in addresses}
        if not self.compact:
            return choose(key, {**{address: 1 for address in self.exceptions}, **ram}, 0)
        return f'calc({self.contains(key)} + ({choose(key, ram, 0)}))'

    def lookup(self, key, choose, extra=None, valid=None):
        if self.mbc1:
            # All five bus lanes translate independently using OLD controller
            # state. Zero adjustment precedes the physical address-line mask.
            physical = f'cart-{key}'
            banks = len(self.data) // 16384
            self.lookup_expr[physical] = f'calc(mod(var(--{key}),16384) + min(1,round(down,var(--{key}) / 16384)) * mod(max(1,var(--mbc-bank)),{banks}) * 16384)'
            selected = self.paged_lookup(physical, choose) if self.paged else choose(physical, self.exceptions, self.fill)
            selected = choose(key, extra or {}, selected)
            return f'calc(255 + ({valid or self.contains(key)}) * (({selected}) - 255))'
        table = {**self.exceptions, **(extra or {})}
        if not self.compact:
            # Preserve the small embedded cartridges' original lookup graph.
            # Avoid new range dependencies in the already timing-sensitive
            # automatic pipeline when a large address range is not needed.
            return choose(key, table, 255)
        if self.paged:
            selected = choose(key, extra or {}, self.paged_lookup(key, choose))
        else:
            selected = choose(key, table, self.fill)
        # Padding is still mapped ROM, including zero bytes. Out-of-range fetch
        # is rejected by the CPU fetch-validity gate (FF itself is valid RST).
        return f'calc(255 + ({valid or self.contains(key)}) * (({selected}) - 255))'
