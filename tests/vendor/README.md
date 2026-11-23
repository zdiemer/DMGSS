# Independent CPU data

These are expected results from upstream projects, never calculated by DMGSS.
Both datasets are MIT-licensed; each directory contains the upstream notice.
`manifest.json` records commit pins, original-file hashes and generated-file
hashes. Network access is not required for CI.

- [Mooneye Test Suite](https://github.com/Gekkio/mooneye-test-suite/tree/31510e12eea6286d36eea060a6adde755e1067aa):
  all 4,096 rows from `acceptance/instr/daa.s`. Upstream reports these DAA
  results verified on DMG and several other Game Boy models. Each row is
  `[input A, input F, output A, output F]`; four-bit flag literals are shifted
  into the actual register's upper nibble. No expected result is recomputed.
- [SingleStepTests SM83](https://github.com/SingleStepTests/sm83/tree/f9c30210245dd691661db39f5ace022c465ecc2f):
  32 unchanged JSON records for each of 80 ALU/rotate/flag opcodes and all
  256 CB-prefixed opcodes (8,192 additional cases in `sm83/cb.json`). Selection
  takes the first example of every observed output-flag pattern, then the
  earliest remaining records to 32. `[HL]` cases aliasing an instruction byte
  are excluded because the fixture adapter relocates data. This is a sample,
  not the entire upstream corpus. These vectors are generated from an Ares
  translation; they are an independent software oracle, not hardware captures.

Regenerate from clean checkouts at the pinned commits:

```sh
python3 tools/import_conformance.py --mooneye /path/to/mooneye-test-suite --sm83 /path/to/sm83
```

The browser fixtures relocate PC to 0100 and `[HL]` data to C000. All other
register inputs and expected outputs remain upstream values. CB memory results
are copied directly from upstream final RAM, including read-modify-write cases. They compare
instruction-level state, not bus cycles, interrupts, IME or IE. See
[the compatibility report](../../docs/COMPATIBILITY.md) for the exact boundary
between these checks and running complete test ROMs.

`sm83/high.json` adds 32 records for each of eight RST and four LDH opcodes.
RST candidates keep PC below 8000 and exclude stack/instruction aliases; PC and
upstream pushed return bytes are unchanged, while SP and its two stack bytes
move into HRAM. LDH candidates address FF80–FFFE and exclude instruction/data
aliases; those actual HRAM addresses and expected values are retained. The
fixture's two ROM slots are seeded at generation time to preserve RST PCs.
Cycles and interrupt state remain outside the comparison.
