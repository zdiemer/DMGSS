# Compatibility and external tests

DMGSS is still a CPU experiment, not a game-compatible Game Boy emulator.
Browser execution remains HTML/CSS-only. Python converts data and emits generic
CPU stages; it never emulates ROM instructions or precomputes their execution.

## Current evidence

Build 12 supports 240 unprefixed instructions and all 256 CB-prefixed
operations: RLC/RRC/RL/RR, SLA/SRA/SRL, SWAP, BIT, RES and SET. Earlier
8-bit ALU, accumulator rotates, decimal adjustment, load, branch, register-pair
and stack support is retained.
All eight RST vectors and four LDH forms are implemented. HRAM FF80–FFFE
is readable, writable and executable; mapped work RAM and VRAM are executable
too. FF00–FF7F I/O registers and FFFF interrupt enable remain unmapped and trap.
Unknown opcodes, missing instruction bytes and unsupported accesses trap atomically.

The CSS CPU is checked against **15,232 independent input/output cases**:

- All 4,096 input combinations in Mooneye's hardware-verified DAA table.
- 2,560 sampled SingleStepTests SM83 vectors, covering 80 ALU/rotate/flag
  opcodes, with 32 cases each and every observed output-flag pattern included.
- 8,192 sampled SM83 CB vectors: 32 per opcode, checking final registers, flags
  and memory directly against upstream results.
- 384 sampled SM83 RST/LDH vectors: 32 per opcode. RST keeps upstream PC and
  return bytes, relocating only SP/stack addresses into HRAM; LDH samples use
  actual mapped HRAM addresses and retain their upstream memory results.

Chromium runs both the arithmetic and native `if()` CSS paths; WebKit runs the
arithmetic path. These are single-instruction kernel checks with fixed initial
state emitted before loading. Page JavaScript is disabled. Browser automation
only reads computed results; it never writes CPU state or clocks execution.
Expected values remain in the test runner, not in the generated page.

Except for RST, the adapter moves the instruction to 0100; `[HL]` data moves
to C000 for the earlier ALU/CB cases. This is because the
upstream SM83 corpus assumes flat 64 KiB RAM. Register values and expected ALU
results are otherwise preserved. Bus cycles, interrupts, IME and IE are not
scored. This is **not a claim that the full Mooneye or Blargg ROMs pass**.
Pins, hashes, licenses and reproduction instructions are in
[`tests/vendor`](../tests/vendor/README.md).

End-to-end browser tests also run original ROM programs through all four
execution modes, including carry retention across automatic and manually copied
bank transfers, memory-read traps and a self-checking ALU lab. The [Bit lab](https://dmgss.zachd.duckdns.org/automatic/bits/) also checks
CB register and RAM/VRAM operations. The public
[ALU lab](https://dmgss.zachd.duckdns.org/automatic/alu/) exercises decimal
arithmetic, carry, bitwise logic and rotations without JavaScript.

## Whole-ROM targets and blockers

| Upstream suite | Intended use | Current status |
| --- | --- | --- |
| [Mooneye](https://github.com/Gekkio/mooneye-test-suite) (MIT) | CPU and hardware behavior verified on real devices | DAA table is used above. The unmodified DAA ROM additionally needs broader work RAM and hardware I/O, a larger ROM lookup, and its result/printing harness. Timing and interrupt tests need those hardware units. |
| [Blargg CPU tests](https://github.com/retrio/gb-test-roms/tree/c240dd7d700e5c0b00a7bbba52b53e4ee67b5f15/cpu_instrs) | Broad instruction behavior and checksums | Not run or bundled. Inspected `01-special.gb` and `04-op r,imm.gb` declare MBC1 and exceed our 1,024-exception lookup limit (1,815 and 2,640 exceptions respectively). The harness also needs additional CPU, memory and hardware behavior. No header patch or synthetic pass is applied. |
| [GBMicrotest](https://github.com/aappleby/GBMicrotest/tree/463eb6bc0fe31d61781ef63060ad6d74090c0255) (MIT) | Small cycle-accuracy and hardware-quirk tests | Deferred: upstream explicitly assumes an already functional emulator. Current gaps include I/O, interrupts, PPU and cycle accounting; its headers also declare cartridge hardware we reject. |
| [dmg-acid2](https://github.com/mattcurrie/dmg-acid2) | DMG graphics output | Future target after a real PPU, tile maps, sprites and LCD registers exist. A one-tile viewer cannot establish a pass. |

## Next milestones

1. Interrupt state and delivery, DI/EI/RETI, HALT/STOP behavior and hardware
   I/O. These require real semantics, not no-op decoder entries. Broaden work RAM.
2. Scalable dense ROM lookup and cartridge controllers. Do not silently patch
   headers or bypass the converter's bounds to make a suite appear accepted.
3. Cycle accounting, timers, serial test output and interrupt/HALT behavior,
   then unmodified CPU test ROMs with their actual completion protocol.
4. PPU and input milestones, graphics tests and open-source game compatibility.

Passing instruction-state checks does not establish timing, complete memory
mapping, hardware compatibility or practical game speed.

CB fetch consumes both bytes in one instruction tick. A missing second ROM
byte traps without retiring. BIT performs a read only, so mapped ROM is legal;
other `[HL]` CB forms require writable memory even when the value would not
change. Rejected accesses preserve registers, flags, memory, PC and ticks.

The [High RAM lab](https://dmgss.zachd.duckdns.org/automatic/high/) calls all
restart vectors, uses both LDH addressing forms, and executes a routine written
into HRAM during the run. Separate tests fill every HRAM byte and transfer a
live restart return address across automatic and manual banks. Fetch validation
is explicit now that FF is a valid RST instruction: missing bytes never become
synthetic calls. All operands are validated even for untaken branches.
