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
instruction-level state and duration, not bus ordering, interrupts, IME or IE. See
[the compatibility report](../../docs/COMPATIBILITY.md) for the exact boundary
between these checks and running complete test ROMs.

`sm83/high.json` adds 32 records for each of eight RST and four LDH opcodes.
RST candidates keep PC below 8000 and exclude stack/instruction aliases; PC and
upstream pushed return bytes are unchanged, while SP and its two stack bytes
move into HRAM. LDH candidates address FF80–FFFE and exclude instruction/data
aliases; those actual HRAM addresses and expected values are retained. The
fixture's two ROM slots are seeded at generation time to preserve RST PCs.
Instruction durations use four times the upstream M-state array length; bus
ordering and interrupt state remain outside this comparison.


`sm83/interrupts.json` adds 96 raw DI/EI/RETI records from the same pin, selecting
32 per opcode with every observed output-flag/initial-IME pair. RETI instruction/
stack alias cases are excluded. The adapter preserves registers, upstream IME
and the final `ei` latch; RETI relocates only SP/stack lanes, retaining its exact
upstream target and byte values. As with earlier datasets, the cycle array supplies instruction duration; its
bus ordering and the corpus's unrelated initial `ie` metadata are not scored. New independent total:
15,328 cases. Original multi-instruction interrupt regressions are separate.


`sm83/timing.json` preserves 258 raw records: the first example of each observed
M-state count for every ordinary unprefixed instruction. HALT is excluded because
upstream includes idle samples, STOP is unsupported, and CB is already covered
above. The timing-only adapter keeps opcode and initial flags but replaces
registers/operands with mapped addresses; only retirement and total duration
are compared. This covers 242 instructions and both paths of 16 conditions.
Expected T-cycles are four times each record's `cycles` length. These are not
additional full-state or whole-ROM passes. Original timing edge cases are
separate and have no upstream provenance claim.


`mooneye/timer/*.s` contains eleven unchanged sources from the same pinned MIT
suite. Their comments report hardware-verified assertions. `timer_fixtures.py`
assembles the `test:` body verbatim in instruction order at 0100, replacing the
setup_assertions/printing tail with XOR A, LDH [TAC],A, HALT. That tail preserves
all upstream assertion registers. The independent expected registers are read
from the source; uppercase hex is supported. No boot/setup/printing harness or
whole-ROM compatibility is claimed. Each source and output has a manifest hash;
regeneration uses the same import command above.


`mooneye/mbc1/rom_512kb.s` and `rom_1Mb.s` are unchanged MIT-licensed
64/128 KiB bank tables from the same Mooneye pin. Their comments report testing
on a genuine MBC1B1 cartridge. `mbc1/manifest.json` pins paths and SHA-256 hashes.
The browser runner reads the 384 table entries per source directly, exercising
all 128 selections in both modes with original programs. The switched-window
table is used in both modes: 512 observations per source, 1,024 overall. No
upstream harness is executed. Regenerate with:

```sh
python3 tools/import_mbc1.py --mooneye /path/to/pinned/mooneye-test-suite
```
