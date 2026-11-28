# Compatibility and external tests

DMGSS is still a CPU experiment, not a game-compatible Game Boy emulator.
Browser execution remains HTML/CSS-only. Python converts data and emits generic
CPU stages; it never emulates ROM instructions or precomputes their execution.

## Current evidence

Version 0.22.0 supports 243 unprefixed instructions and all 256 CB-prefixed
operations: RLC/RRC/RL/RR, SLA/SRA/SRL, SWAP, BIT, RES and SET. Earlier
8-bit ALU, accumulator rotates, decimal adjustment, load, branch, register-pair
and stack support is retained.
All eight RST vectors and four LDH forms are implemented. HRAM FF80–FFFE
is readable, writable and executable; mapped work RAM and VRAM are executable
too. Serial registers (FF01–FF02), timer registers (FF04–FF07), IE (FFFF), IF (FF0F), and LCDC/STAT/LY/LYC (FF40/FF41/FF44/FF45) and BGP (FF47) are mapped. Other
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
| [Mooneye](https://github.com/Gekkio/mooneye-test-suite) (MIT) | CPU and hardware behavior verified on real devices | DAA table is used above. The unmodified DAA ROM additionally needs hardware I/O, its result/printing harness and cartridge setup. Dense lookup now accepts full 32 KiB ROM-only images. Eleven reduced timer bodies are also used below. The complete ROM harness still needs the broader hardware/memory map. |
| [Blargg CPU tests](https://github.com/retrio/gb-test-roms/tree/c240dd7d700e5c0b00a7bbba52b53e4ee67b5f15/cpu_instrs) | Broad instruction behavior and checksums | Not run or bundled. Inspected `01-special.gb` and `04-op r,imm.gb` declare MBC1; ROM-only MBC1 up to 128 KiB is now accepted. The former density blocker (1,815 and 2,640 exceptions respectively) is removed by paged lookup. The harness also needs additional CPU, memory and hardware behavior. No header patch or synthetic pass is applied. |
| [GBMicrotest](https://github.com/aappleby/GBMicrotest/tree/463eb6bc0fe31d61781ef63060ad6d74090c0255) (MIT) | Small cycle-accuracy and hardware-quirk tests | Deferred: upstream explicitly assumes an already functional emulator. Current gaps include most I/O, interrupt bus timing, PPU and cycle-by-cycle peripheral timing; its headers also declare cartridge hardware we reject. |
| [dmg-acid2](https://github.com/mattcurrie/dmg-acid2) | DMG graphics output | Future target after a real PPU, tile maps, sprites and LCD registers exist. A one-tile viewer cannot establish a pass. |

## Next milestones

1. Additional interrupt sources;
   STOP behavior. STOP still traps explicitly.
2. Larger MBC1 cartridges, cartridge RAM and other controllers. Do not silently patch
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
bus operations, interrupt cancellation during stack writes, or general IE/IF races.
Timers and internal serial transfers request interrupts independently and wake HALT.
LCD and joypad sources remain unimplemented. Original seeded wakeup regressions are
retained alongside the timer-driven programs.
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
This counter accounts for instruction/entry work, not idle time or wall time.
The timer and serial circuits below advance separately during HALT waits.
PPU, DMA and a complete CPU bus scheduler remain future work.


## Timer circuit (0.14.0)

DIV exposes the high byte of a separate 16-bit divider. TIMA selects falling
edges at periods of 1024, 16, 64 or 256 T-cycles through TAC. DIV resets and
TAC changes apply the monochrome falling-edge behavior. TAC reads F8 in its
unused bits. TIMA overflow leaves zero for one M-cycle, then loads TMA and
requests IF bit 2. TIMA writes can cancel a pending reload; during the reload
M-cycle they are ignored, and a TMA write supplies the value loaded into TIMA.
The circuit follows [Pan Docs timer behavior](https://gbdev.io/pandocs/Timer_Obscure_Behaviour.html).

Eleven unchanged MIT-licensed assembly sources from the existing Mooneye pin
are vendored: tim00/01/10/11, their four div_trigger variants, tima_reload,
tima_write_reloading and tma_write_reloading. A small strict assembler encodes
their exact `test:` bodies, relocates them to 0100 and replaces the assertion/
printing harness with timer shutdown and HALT. The test runner compares the
original register assertions, including uppercase hex literals. Python only
assembles bytes. These are **reduced program passes, not unmodified Mooneye ROM
passes**; boot, suite setup and result-printing code are not executed.

The original [Timers lab](https://dmgss.zachd.duckdns.org/automatic/timers/)
starts TIMA near overflow, sleeps with HALT, handles the actual timer request,
records the reloaded TIMA, disables the timer and returns. It finishes at 36
instructions / 360 CPU-work T-cycles in all modes. Separate tests transfer a
pending overflow and sleeping CPU across automatic/manual banks, check timer
progress with zero retired instructions, and run timer programs through upload.

Limits are deliberate and visible: CPU instructions and word transfers still
retire atomically. Six generic M-cycle lanes advance the timer for the accepted
instruction/interrupt duration; data reads observe the final M-cycle, and all
CPU writes occur at its final boundary. Fetches use the old bank. This does not
model individual bus accesses, two-lane word-write ordering, arbitrary T-cycle
phases or all IF/write races. Explicit IF writes win at the final boundary.
STOP and CGB timer differences remain unsupported. A rejected fetch/transfer
freezes the timer as part of the experiment's atomic-trap contract.

HALT consumes one four-T-cycle timer step while TAC is enabled, a reload is
pending, an internal serial transfer is active, or the LCD is enabled, without retiring an instruction or increasing the CPU-work counter.
Timer requests wake HALT with IME off too, if IE enables the request. With no
live timer/reload/internal serial transfer/LCD and no enabled pending request, the experiment is quiescent:
all clocks freeze, including DIV. It does not represent free-running hardware
observed by future external inputs. Pause freezes all clocks. Timer waits and
interrupt entries share the 128-stage batch budget; the instruction count can
stay below 128 while a bounded run still exhausts that budget.


## Serial milestone and limits

SB (FF01) and SC (FF02) implement a disconnected DMG serial port. With internal
clock selected, each 512 accepted T-cycles shifts one outgoing bit, MSB first,
and shifts in one. Eight shifts receive FF, clear SC bit 7 and request IF bit 3.
SC bits 1–6 read as one. External-clock transfers stay armed without progress;
there is no cable peer or source of external pulses. Internal transfers advance
while HALT waits, even with IE/IME off, and can wake the CPU through the existing
interrupt dispatcher. Timer and serial requests can coexist.

The behavior follows [Pan Docs serial transfer](https://gbdev.io/pandocs/Serial_Data_Transfer_(Link_Cable).html).
The unused-bit expectations also match the pinned Mooneye
[unused_hwio-GS source](https://github.com/Gekkio/mooneye-test-suite/blob/31510e12eea6286d36eea060a6adde755e1067aa/acceptance/bits/unused_hwio-GS.s).
Original tests check shifts, rates, masks, requests, atomic/rejected writes,
partial-byte retention, pauses, resets, IF arbitration and log rollover. These
are not whole-ROM serial-suite passes. The upstream boot_sclk_align test needs
boot state and clock alignment that this experiment does not implement.

The serial monitor is diagnostic state, not additional Game Boy memory. It
keeps the latest 16 completed outgoing bytes, oldest first, alongside a 16-bit
wrapping transfer count. Printable ASCII is shown as text, LF/CR/TAB as marks,
and other bytes as dots; the hex row preserves exact values. Actual shifted-out
bits are recorded, including SB changes during a transfer. Incomplete/aborted
transfers never append a byte. The monitor also works in uploaded and offline
converted pages, without requests or scripts during execution.

Timing remains approximate: every SC write resets the transfer phase and bit
counter; the first internally clocked bit follows 512 T-cycles later. This is
not the hardware's free-running divider alignment, DIV-write coupling, active
SC-write race behavior, or CGB fast serial. Reads see the final instruction
boundary, then explicit writes apply. Completion at that boundary is recorded
before a simultaneous CPU write. CPU-work T-cycles still exclude HALT idle time;
Pause/fault/atomic traps freeze both peripherals.

[Serial lab](https://dmgss.zachd.duckdns.org/automatic/serial/) sends OK using
HALT/interrupt return and SC polling. A byte takes 4,096 T-cycles, so the lab
needs multiple batches. Compatible mode correctly stops with a partial
transfer; it does not fake completion to fit 128 stages. Automatic mode runs
the whole lab, manual mode needs repeated bit saves, and streaming mode is slow.

## Dense ROM lookup (0.16.0)

Compatible, Automatic and Manual modes accept any byte density within the
existing 32 KiB ROM-only and 4 KiB raw bounds. Files with more than 1,024 exceptions to their most common
byte use 256-byte pages. Two bytes share a 16-bit value; CSS selects a page and
pair, then extracts the addressed byte. Identical pages share selectors. All
bytes are encoded independently of execution, including unreachable bytes.
The compiler never runs the ROM or patches its header. Streaming retains its
1,024-exception limit: CI observed its animation banks failing to initialize
a dense document even though isolated native lookup probes passed. Conversion
rejects this combination with a mode-selection message instead of emitting an
unreliable run. The 0.19.0 scroll-storage replacement retains this cap pending
separate dense-streaming validation.

Original browser probes compare scattered addresses, every page edge and all
byte offsets against the input bytes in both arithmetic and native CSS paths.
End-to-end dense programs exercise immediate fetch across pages, both word-read
lanes, ROM/VRAM crossings, wrap from IE to ROM, invalid writes, raw-range traps,
automatic continuation, manual continuation with dense repeating pages, reset
and offline downloads. The original dense
sample checks nine scattered bytes; it is not an upstream suite pass. Existing
instruction and hardware suites remain the independent CPU evidence above.

No extra writable memory, banking, boot state, hardware accuracy or game-speed
claim accompanies this change. Worst-case documents stay below a tested 12 MiB
budget; large files still cost browser time and memory. Numeric precision in
[CSS Values](https://www.w3.org/TR/css-values-4/#numeric-types) is implementation-defined;
packed values stay within 0–65,535 and are tested on Chromium and Linux WebKit.
Actual iOS validation remains separate.


## Work RAM and echo (0.17.0)

Work RAM now covers 256 physical bytes at C000–C0FF with a shared echo mirror
at E000–E0FF. This is still a subset of DMG's 8 KiB work RAM. Unimplemented
physical bytes and their mirrors trap; OAM and cartridge RAM remain unsupported.
The [memory map](https://gbdev.io/pandocs/Memory_Map.html#echo-ram) defines echo
as an alias, so there is only one retained byte for each physical location.

Original tests exercise both alias directions, CB writes, two-byte stores,
code written in RAM and called through echo, interrupt entry/RETI through an
echo stack, and atomic failures at the new boundary. An automatic program
writes all 256 distinct byte values over 770 instructions. Separate automatic
and manual runs retain the added addresses through bank swaps. The loader's
original RAM sample halts after 24 instructions with A=165; it is not a new
upstream ROM pass. Existing upstream vectors remain unchanged; original trap
fixtures move from the former C040 boundary to C100.


## Compact automatic storage (0.18.0)

Automatic mode now stores two adjacent physical RAM bytes per 16-bit scroll
cell. Its storage uses 499 cells instead of 897 while preserving all 448 CPU
fields. Work RAM remains 256 bytes; this change prepares storage for later
expansion. Other execution modes and their memory maps are unchanged.

Original browser checks exercise exact offset 65,535, wrapped initial values,
three-batch low/high byte changes, independent FFFE/FFFF state, cross-pair word
writes, atomic traps and reset. Existing whole-page RAM/HRAM fills and CPU,
interrupt, timer and serial checks remain required. Automatic downloads are
also exercised offline. This adds storage evidence, not new upstream ROM passes
or a real-device iOS certification. Fewer cells do not imply real-time speed.


## Full work RAM (0.19.0)

C000–DFFF now covers all 8 KiB, with E000–FDFF sharing C000–DDFF. There is no
FE00 alias for DE00. OAM, full VRAM/PPU, cartridge banking and general bus timing
remain separate work. The original RAM sample still ends at 24 instructions and
A=165, now touching both WRAM banks and the top byte.

Original regression coverage checks page-crossing words, executable code crossing
CFFF/D000 and EFFF/F000, high physical/echo stacks, invalid echo-end accesses,
all 8,192 independently seeded bytes through automatic continuation, and cells
returning to their initial value before later writes. These are original tests,
not new upstream ROM passes. Existing upstream vectors are unchanged; original
unmapped-memory fixtures move to FE00 or the FDFF/FE00 boundary.

Full-map documents are much larger. Worst-case converter budgets are 12 MiB for
Compatible, 24 MiB for Automatic, and 96 MiB for Manual. Automatic storage has
16,627 cells; Manual has 132,522 bits per bank (including LCD timing and BGP state). Browser resource limits and mobile
performance remain material constraints. Linux WebKit testing does not certify
this expanded memory on real iOS devices.


## MBC1 ROM banking (0.20.0)

ROM-only MBC1 (type 01, no cartridge RAM) accepts exactly 32, 64 or 128 KiB
with matching size headers. The low five-bit bank register starts at zero;
reads map zero to one before applying the physical ROM address-line mask.
All five fetch/data lanes translate independently; logical PC/SP are preserved.
Control writes do not mutate ROM. RAM-enable, upper-bank and mode writes have
no observable effect on this supported cartridge configuration. Larger wiring,
MBC1M and cartridge RAM are not implemented; A000–BFFF still traps explicitly.

The semantics follow [Pan Docs MBC1](https://gbdev.io/pandocs/MBC1.html).
Two unchanged pinned Mooneye bank tables provide 768 independent expected table entries and 1,024 checked
observations (fixed window in both modes and switched window in both modes,
for 64 and 128 KiB). Original byte programs exercise all 128 combined bank
selections, compare actual CSS reads to those tables, and never embed expected
results in the generated emulator. These are bank-map checks, not executions
of the original ROM harness or new whole-ROM passes.

Original tests cover banked code/data, bank-zero masking, bank writes during
switched execution, split fetch/data lanes, native reset, offline downloads,
and bank retention through Automatic and Manual continuation. Word transfers
retain atomic validation; controller conflicts use low-then-high order for
LD [nn],SP and high-then-low order for stack writes. This determines the final
bank register, without introducing individual bus cycles or full bus timing.
Dense Streaming imports retain their existing explicit limit.


## LCD timing foundation (0.21.0)

LCDC (FF40), STAT (FF41), LY (FF44, read-only) and LYC (FF45) are mapped.
LCDC starts off; STAT reads 84. Enabling LCDC bit 7 starts line 0 in mode 2.
Disabling it resets the internal line/dot and LY to zero and suppresses LCD
requests. Other LCDC bits retain their values but have no rendering effect yet.

The fixed-duration model uses 154 lines of 456 T-cycles: visible lines use
80 dots in mode 2, 172 in mode 3 and 204 in mode 0; lines 144–153 use mode 1.
LY reports zero from dot 4 of internal line 153, while mode 1 lasts until the
frame wraps. VBlank requests IF bit 0 on entry to line 144. Mode 0/1/2 and
LY=LYC conditions selected by STAT bits 3–6 share one ORed signal; only its
rising edge requests IF bit 1. Consecutive active sources therefore block
retriggering. STAT bit 7 reads high; bits 0–2 and LY ignore CPU writes.

Timing follows the documented baseline in [Pan Docs rendering](https://gbdev.io/pandocs/Rendering.html),
[LCD status](https://gbdev.io/pandocs/STAT.html) and
[interrupt sources](https://gbdev.io/pandocs/Interrupt_Sources.html).
This is an **approximation**, not a full or cycle-accurate PPU: mode 3 does not
vary, startup begins immediately, and the DMG STAT-write glitch, special
mode-2 request at VBlank entry, model-specific LY/LYC comparison delays and
sub-M-cycle races are not implemented. VRAM/OAM access restrictions, pixels,
scrolling, sprites and DMA remain absent. No PPU test-ROM pass is claimed.

Six generic M-cycle lanes sample the LCD alongside timers. Data reads see the
final clocked boundary; writes retire atomically afterwards. LYC/STAT/LCDC
writes can raise the shared signal. Read-modify-write instructions read the
clocked IF/STAT before applying their own data; explicit IF writes win over
all hardware requests. Pause, faults and rejected transfers freeze the clock.
Enabled LCD timing continues during HALT even with IE/IME off, without adding
retired instructions or CPU-work T-cycles. All LCD state participates in the
complete-bank handshake.

Original browser contract cases cover boundaries, signal blocking, register
masks, write requests, simultaneous timer/serial/LCD requests and atomic traps.
The [LCD lab](https://dmgss.zachd.duckdns.org/automatic/lcd/) starts from reset,
waits for scanline 2 and wakes through STAT. Compatible mode stops mid-wait;
automatic and manual continuation carry it to completion. Generation-time
boundary fixtures exercise VBlank without waiting an entire CSS-driven frame.
These fixtures supply initial states, never execution traces or runtime writes.


## Background palette (0.22.0)

BGP (FF47) is an eight-bit readable/writable register. Each two-bit field maps
one background/window color ID to shade 0–3, as specified by
[Pan Docs palettes](https://gbdev.io/pandocs/Palettes.html#ff47--bgp-non-cgb-mode-only-bg-palette-data).
The tile viewer first decodes the two VRAM bitplanes into IDs, then applies BGP
and the console's four green shades. Background ID 0 is opaque, not transparent.
BGP starts at zero in this experiment; the built-in tile ROM explicitly writes
E4 for the identity mapping. This is not a boot-ROM/post-boot register image.

The original Palette lab copies the tile, continues past a 128-stage boundary,
then writes 1B to reverse its shades and reads the register back. VRAM stays
unchanged. Compatible mode stops with E4; Automatic, Manual and Streaming finish
with 1B. Register writes survive bank copying, pause and offline conversion.
Original tests check all 256 palettes × four IDs, CPU reads/writes, CB operations,
reset and atomic traps at FF46/FF48. These are register/renderer contracts,
not a whole-ROM or PPU-suite pass.

The viewer reads current committed VRAM/BGP and remains a debugging view even
with LCDC off. It does not model per-pixel palette sampling, mid-scanline effects,
LCD blanking, a frame buffer, full VRAM, tile maps, windows, sprites or OBJ/CGB
palettes. FF48/FF49 remain unmapped; LCD timing retains its previous limitations.


## Full VRAM (build 0.23)

The full 8000–9FFF range is writable and executable, following the
[Pan Docs memory map](https://gbdev.io/pandocs/Memory_Map.html#vram-memory-map). Original contracts cover
both decoders, packed byte lanes, page boundaries, stack access, truncated fetch,
9FFF/A000 atomic failures and separation from WRAM echo. A seeded full-map test
checks all 8,192 bytes after automatic bank copies; reactivation covers zero and
nonzero initial words. The last-page lab crosses a manual/automatic checkpoint.
These are original memory contracts, not an upstream whole-ROM pass. Existing
pinned CPU expectations are unchanged; the original unmapped-CB timing case
moves from newly supported 9000 to still-unmapped A000.

The tile viewer still displays only 8000–800F. LCD mode-3 access restrictions,
background/window rendering, OAM, sprites and DMA remain unimplemented. Resource
requirements have grown; Linux WebKit coverage is not real-device iOS approval.
