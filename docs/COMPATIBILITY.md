# Compatibility and external tests

DMGSS is still a CPU experiment, not a game-compatible Game Boy emulator.
Browser execution remains HTML/CSS-only. Python converts data and emits generic
CPU stages; it never emulates ROM instructions or precomputes their execution.

## Current evidence

Build 14 supports 243 unprefixed instructions and all 256 CB-prefixed
operations: RLC/RRC/RL/RR, SLA/SRA/SRL, SWAP, BIT, RES and SET. Earlier
8-bit ALU, accumulator rotates, decimal adjustment, load, branch, register-pair
and stack support is retained.
All eight RST vectors and four LDH forms are implemented. HRAM FF80–FFFE
is readable, writable and executable; mapped work RAM and VRAM are executable
too. IE (FFFF) and IF (FF0F) are mapped with their register semantics. Other
I/O addresses remain unmapped and trap. DI, delayed EI, RETI, interrupt priority
and instruction-level HALT behavior are implemented.
Unknown opcodes, missing instruction bytes and unsupported accesses trap atomically.

The CSS CPU is checked against **15,328 independent input/output cases**:

- All 4,096 input combinations in Mooneye's hardware-verified DAA table.
- 2,560 sampled SingleStepTests SM83 vectors, covering 80 ALU/rotate/flag
  opcodes, with 32 cases each and every observed output-flag pattern included.
- 8,192 sampled SM83 CB vectors: 32 per opcode, checking final registers, flags
  and memory directly against upstream results.
- 384 sampled SM83 RST/LDH vectors: 32 per opcode. RST keeps upstream PC and
  return bytes, relocating only SP/stack addresses into HRAM; LDH samples use
  actual mapped HRAM addresses and retain their upstream memory results.
- 96 sampled SM83 DI/EI/RETI vectors: 32 per opcode, including IME and the EI
  delay latch. RETI preserves the upstream return target and stack bytes; only
  its stack location moves to C000/C001.

Chromium runs both the arithmetic and native `if()` CSS paths; WebKit runs the
arithmetic path. These are single-instruction kernel checks with fixed initial
state emitted before loading. Page JavaScript is disabled. Browser automation
only reads computed results; it never writes CPU state or clocks execution.
Expected values remain in the test runner, not in the generated page.

Except for RST, the adapter moves the instruction to 0100; `[HL]` data moves
to C000 for the earlier ALU/CB cases. This is because the
upstream SM83 corpus assumes flat 64 KiB RAM. Register values and expected ALU
results are otherwise preserved. The new control cases score IME and the
upstream EI latch; older arithmetic cases do not. The 11,232 SM83 cases also compare instruction duration against four times the
upstream M-state count. Bus ordering and peripheral interrupt generation remain
unscored. This is **not a claim that the full Mooneye or Blargg ROMs pass**.
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
| [GBMicrotest](https://github.com/aappleby/GBMicrotest/tree/463eb6bc0fe31d61781ef63060ad6d74090c0255) (MIT) | Small cycle-accuracy and hardware-quirk tests | Deferred: upstream explicitly assumes an already functional emulator. Current gaps include most I/O, interrupt bus timing, PPU and cycle-by-cycle peripheral timing; its headers also declare cartridge hardware we reject. |
| [dmg-acid2](https://github.com/mattcurrie/dmg-acid2) | DMG graphics output | Future target after a real PPU, tile maps, sprites and LCD registers exist. A one-tile viewer cannot establish a pass. |

## Next milestones

1. Timers and serial output with real interrupt sources;
   STOP behavior and broader work RAM. STOP still traps explicitly.
2. Scalable dense ROM lookup and cartridge controllers. Do not silently patch
   headers or bypass the converter's bounds to make a suite appear accepted.
3. Unmodified CPU test ROMs with their actual completion protocol, plus
   cycle-accurate interrupt entry, register-write races and HALT timing.
4. PPU and input milestones, graphics tests and open-source game compatibility.

Passing instruction-state and duration checks does not establish bus timing, complete memory
mapping, hardware compatibility or practical game speed.

CB fetch consumes both bytes in one instruction tick. A missing second mapped
byte traps without retiring. BIT performs a read only, so mapped ROM is legal;
other `[HL]` CB forms require writable memory even when the value would not
change. Rejected accesses preserve registers, flags, memory, PC and ticks.

The [High RAM lab](https://dmgss.zachd.duckdns.org/automatic/high/) calls all
restart vectors, uses both LDH addressing forms, and executes a routine written
into HRAM during the run. Separate tests fill every HRAM byte and transfer a
live restart return address across automatic and manual banks. Fetch validation
is explicit now that FF is a valid RST instruction: missing bytes never become
synthetic calls. All operands are validated even for untaken branches.

## Interrupt milestone limits

[Interrupts lab](https://dmgss.zachd.duckdns.org/automatic/interrupts/) requests
all five interrupts through IF, records their priority order in RAM, returns
with RETI, then verifies the HALT bug. Original regressions cover EI→DI, EI→EI,
EI→HALT, duplicated immediate/CB/RST fetches, atomic stack failures, and delayed
enable/live interrupt frames/HALT-bug state across retention banks.

The behavior follows [Pan Docs interrupts](https://gbdev.io/pandocs/Interrupts.html)
and [HALT](https://gbdev.io/pandocs/halt.html). Register-bit expectations agree
with Mooneye's [unused_hwio-GS](https://github.com/Gekkio/mooneye-test-suite/blob/31510e12eea6286d36eea060a6adde755e1067aa/acceptance/bits/unused_hwio-GS.s);
EI-sequence and EI/HALT cases are informed by Mooneye's
[ei_sequence](https://github.com/Gekkio/mooneye-test-suite/blob/31510e12eea6286d36eea060a6adde755e1067aa/acceptance/ei_sequence.s)
and SameSuite's [ei_delay_halt](https://github.com/LIJI32/SameSuite/blob/master/interrupt/ei_delay_halt.asm).
These original reduced tests do not run those suites' full harnesses.

Interrupt entry is one atomic CSS transition, with no retired instruction tick.
It accounts for 20 T-cycles (five M-cycles), but does not model their individual
bus operations, interrupt cancellation during stack writes, or IE/IF races. No timer, LCD, serial or joypad currently
requests an interrupt independently. Sleeping-CPU wakeup is covered using state
seeded before loading, not simulated hardware events or runtime test writes.
IF starts at E0 (unused bits read as one); IE and IME start at zero. This is an
explicit test start state, not a boot-ROM/post-boot hardware state.


## Cycle accounting (0.13.0)

The Machine inspector displays a 16-bit T-cycle counter, initially zero and
wrapping at 65,536 in every mode. Each successful instruction adds its DMG
clock duration: conditional JR/JP/CALL/RET use the old flags, CB register forms
cost 8 T-cycles, BIT [HL] costs 12, and other CB memory forms cost 16. Interrupt
entry adds 20 without retiring an instruction. HALT entry adds 4; sleeping,
paused and faulted execution adds nothing. A rejected fetch/data transfer adds
nothing, consistent with this experiment's atomic traps rather than hardware
partial bus activity. Bookkeeping is distinct from elapsed browser time.

An additional **258 independent duration cases** cover all 242 ordinary
unprefixed instructions (excluding HALT and the CB prefix) and both outcomes of
all 16 conditional instructions. Their raw upstream records are preserved; the
adapter retains opcode/flags, places operands in mapped memory, and checks
only duration/retirement, not equivalence of the relocated register results.
Together with the existing CB data, every implemented ordinary instruction's
duration is covered. HALT and interrupt-entry accounting use separate original
regressions informed by the [opcode tables](https://gbdev.io/gb-opcodes/optables/)
and [Pan Docs](https://gbdev.io/pandocs/Interrupts.html).

The new counter is retained atomically across automatic and manual banks,
including wraparound at a boundary. The original diagnostic retires 24
instructions in 196 T-cycles. Tests check that total in all four execution modes,
as well as pause/reset, halted stability, malformed accesses and offline imports.
This is instruction-duration accounting, not a cycle-accurate scheduler: no
peripheral advances during an instruction or while HALT sleeps yet. Timer,
serial, PPU and DMA behavior must build on a future hardware clock model.
