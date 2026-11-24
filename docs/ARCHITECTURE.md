# CSS machine

HTML is the fixed structure, CSS is the runtime, Python is code generation.
The generator emits declarations, never a precomputed sequence of machine states.

A four-phase CSS animation drives two alternating animation banks. The latch
phase copies the previously computed result to the stored bank. The execute
phase samples next-state expressions into the result bank. Paused animations
retain sampled values between phases. Typed integer properties resolve numeric
expressions before they are sampled. This unusual browser behavior is tested
with page JavaScript disabled; it is not a portable general-purpose CSS guarantee.

Power pauses both banks and the clock. Reset navigates to a fresh document.
Browser throttling can slow or skip wall-clock ticks: this is an experimental
instruction clock, not a hardware-accurate oscillator.

Research: [x86CSS](https://github.com/rebane2001/x86CSS) demonstrates autonomous
CSS CPU state storage and a style-query clock; [Jane Ori's CPU hack](https://dev.to/janeori/expert-css-the-cpu-hack-4ddj)
explores CSS feedback. DMGSS uses its own generator and machine implementation.
[Pan Docs](https://gbdev.io/pandocs/) is the hardware reference.

## SM83 subset (build 02)

The original subset shipped with 84 unprefixed opcodes: NOP; HALT; register-to-register LD (excluding [HL]);
LD r8,d8; INC/DEC r8; ADD/SUB/CP d8; XOR A; JP a16; JR and all four JR
conditions; LD [a16],A and LD A,[a16]. Z/N/H/C are packed in the F register.
The addressing milestone below expands this to 127. Instruction fetch reads embedded bytes at 0100. The initial registers are zero,
not a boot-ROM or post-boot register image. Mapped RAM is C000–C03F, FF80–FFFE (HRAM), and one tile at VRAM 8000–800F.

Unknown opcodes and unmapped data accesses trap without advancing PC. HALT
stops execution until reset (interrupt wakeup and the halt bug are not implemented).
The diagnostic performs arithmetic, a RAM roundtrip, comparison and a backwards
loop, then writes A5 to C002 on success. The UI derives success from that memory
byte; it does not set it itself. Inspector values are decimal.

This is instruction-level execution, not cycle-accurate emulation. There is no
PPU, timer, interrupt controller, cartridge banking or audio yet. Stack support
was added in build 08 below.


## Tile lab (build 03)

A separate embedded ROM writes all 16 bytes of an original 8×8 tile, then HALTs.
Each pixel reads the corresponding low/high bitplane bits directly from VRAM:
`shade = bit(low, 7-x) + 2 * bit(high, 7-x)`. CSS selects one of four LCD shades.
The renderer is a magnified tile viewer, not a full 160×144 PPU: tile maps,
sprites, LCD registers, scrolling, DMA and scanline timing are still absent.
Switching cartridges is normal HTML navigation; no runtime ROM parsing is used.


## Browser compatibility and startup checks

Streaming mode relies on Chromium's animated-variable state capture.
Chrome on iOS uses WebKit, not Chromium. A phone-sized Chromium test only
verifies responsive layout/touch interaction; it cannot establish iOS support.

With Playwright 1.65.1's WebKit build 2388, the page parses CSS `if()`, the phase
clock advances, and `--next-pc` computes 258, but `--bank-pc` stays 256 and the
instruction counter stays zero. Syntax detection alone therefore produces a
false positive. Older engines may lack `if()` as well. This was reproduced in
Linux WebKit; it is not a real-device iOS test or a claim about every WebKit release.

The LCD shows an immediate browser limitation when the syntax gate fails. When
syntax is accepted, it displays a startup check until the real instruction
counter advances; after three seconds at zero it reports a stalled engine.
A real opcode fault takes precedence over that message, including a fault on
the very first instruction. The machine remains HTML/CSS-only.

CI runs both modes on desktop and phone-sized Chromium, and portable execution
plus streaming limitation checks on phone-sized WebKit. If WebKit starts advancing correctly, that suite
fails so the support policy can be revisited. The new automatic mode below uses
a different storage design; its counter is now user-confirmed in iOS Chrome,
with broader device/feature validation still pending.


## Bounded compatible mode (build 04)

`/portable/` and `/portable/tile/` execute at most 128 instructions in a fixed
chain of nested HTML elements. Every stage has a read element that inherits
resolved typed `--next-*` integers from its parent and an execute element that
computes new `--next-*` values. The last read element exposes the final state
to the existing display. Wrappers use `display: contents` to preserve layout.

The same SM83 instruction definitions drive both modes. Compatible mode replaces
`if()` selection with mutually exclusive integer gates:
`equals(x, k) = max(0, 1 - abs(x - k))`. Each transition is selected with numeric
arithmetic; registered integer properties resolve expressions before inheritance.
This avoids both CSS `if()` and animated-variable feedback. Style queries still
select display states, and CSS math decodes actual VRAM into pixel colors.

Python repeats **generic interpreter stages**, independent of the ROM's executed
path. It never runs the program or emits a trace. Fetch, decode, branches, flags,
RAM writes and HALT happen in the browser. The Run checkbox gates execution;
clearing it recomputes the initial state. HALT/fault freeze later stages. An
infinite loop reaches 128 instructions and displays STEP LIMIT without pretending
to HALT. There is no retained state between runs, clock, continuation or arbitrary
ROM upload. This is bounded interpretation, not an unbounded emulator solution.

Regression tests run with page JavaScript disabled: all CPU cases, reset,
keyboard activation, the diagnostic, four-shade VRAM rendering, traps and budget
exhaustion. Playwright WebKit 2388 passes; a manual additional check with WebKit
2083 (Playwright 1.48.2, `CSS.supports(if(...))` false) passes the diagnostic,
tile, infinite-loop budget and reset. These are Linux WebKit tests, not iPhone
certification. The user subsequently confirmed Compatible mode works in their iOS Chrome
setup; the OS/browser versions were not supplied. This is separate from
validation of the new checkpoint mode below.


## Manual checkpoints (build 05)

`/checkpoint/` feeds the same 128-stage arithmetic CPU from one of two reusable
native HTML checkbox banks. Each bank now stores 1,770 bits: PC and SP (16 each), eight 8-bit
registers including F, HALT/fault (one each), instruction bookkeeping (16),
and the current 207 bytes of RAM/VRAM/HRAM. A commit checkbox selects the source bank.
No DOM nodes are appended: every run uses the same inputs and CPU stages.

CSS sibling selectors (`input:checked ~ .clock`) expose native bits as numeric
custom properties. Inputs precede the pipeline and stay present when their
visible save labels change. A `:has()` readback prototype produced stale values
in WebKit during touch/keyboard tests, so the shipped mode avoids it.
The pipeline inherits its starting state from the selected bank. At the output,
CSS compares each result bit to the inactive bank, counts differences, and
shows the label for the first differing bit. The index is split into a group
and slot (32 bits per group) for the display queries: in Chromium, the long
minimum expression exposed index 707 while its direct style equality query
failed to show the control. Group/slot queries fix the reproduced case and
cover high RAM bits in the stack continuation test. A **user action** flips that input;
the other labels are hidden. Storage inputs have `tabindex="-1"`; the visible
keyboard link focuses the required input via its fragment, then Space flips it.
Only the current keyboard link participates in normal tab order. Each save leaves
the source bank immutable, so the program's result does not change during copying.
Only when all bits match does the commit control appear. Toggling it swaps banks
and evaluates the next batch. This permits ongoing manually clocked execution
without raising the stage budget or precomputing a ROM execution trace.

This is not automatic state capture: one tap/key activation is needed per
changed bit, plus commit. The counter demo usually takes a few saves per batch;
a program rewriting most of memory can require up to 1,770. Visually hidden storage
inputs hold their native checked state.
There is no disk persistence. Reset/reload restores both banks to their defaults;
pause keeps a partial copy and displays the last committed source state.
HALT or faults hide continuation controls. The diagnostic instruction count
wraps modulo 2^16; emulated 8/16-bit state retains its usual widths.

The original counter cartridge executes LD A,[C000], INC A, LD [C000],A, JR.
One batch advances 32 loop iterations; regression tests reach 1,152 instructions,
including byte wrap, using native mouse/touch/keyboard input with page JS disabled.
Other tests cover partial saves, pause/reset, a later HALT after conditional
branches, all registers, VRAM copied then read back, traps and counter width.

Before the scroll-storage experiment below, experiments with alternating animation
names, forced keyframe invalidation and long-duration/delayed transition banks
did not yield a reliable feedback latch. The manual mode uses ordinary HTML
control state instead of relying on animation snapshot behavior. It requires
real iOS validation independently of the previously confirmed Compatible mode.
A manual check with older WebKit 2083 also passed four batches (512 instructions)
using touch input; current WebKit and Chromium receive the full regression suite.


## Automatic scroll storage (build 06)

`/automatic/` uses the same 128 generic CPU stages, but replaces manual bit copies
with CSS scroll snapping and scroll-driven animations. No click sequence, script,
server request or precomputed ROM trace clocks the machine after Run.

There are now two banks of 220 scroll cells: 13 CPU registers/bookkeeping values and 207 bytes
of RAM/VRAM/HRAM. Each cell's native vertical scroll offset stores an integer. A marker
is positioned at the desired value in pixels; mandatory scroll snapping moves
the offset to it after layout. A named scroll timeline reads the offset into a
registered numeric property on the ancestor clock. Scroll range and animation
range match (255 for a byte, 65,535 for a word, 1 for a bit). Explicit rounding
removes small interpolation errors observed in WebKit. Initial values are encoded
as zero offsets, including PC 0100, so no scripted initialization is needed.

A 441st scroll cell stores which bank is selected. The selected bank is immutable
while the CSS pipeline executes from it. Output markers update only the inactive
bank. CSS compares **every** returned register and memory value to the output;
the selector flips only after they all match. Then the next batch executes from
that committed state. This handshake uses data readiness rather than a timed
copy interval. HALT and faults must commit before they disable subsequent writes.
The UI reads the committed source, never a partially copied destination.

Run enables writes and re-snapping. Pause disables both, retaining offsets and
the last committed state (a queued layout/timeline sample may settle first).
Reset navigates to a fresh document. Bookkeeping wraps at 2^16, independently of
8/16-bit emulated values. The DOM has a constant number of stages and cells.

The timeline scope lives on `body`, outside the animated reader: putting scope
and reader on the same element failed in tested WebKit. Storage cells remain
laid out at a fixed viewport position, transparent, excluded from pointer input,
the tab order and the accessibility tree. `display:none` would deactivate the
timelines. Page scrolling must not write these cells. Scroll anchoring is disabled;
this design uses snap re-alignment, not anchoring.

The UI gates on scroll-timeline, timeline-scope, CSS math and style-query support,
then checks real instruction progress at startup. Syntax support alone does not
establish working storage. A first-instruction trap takes precedence over the
startup warning. Older browsers can use compatible/manual modes. Tests run with
page JavaScript disabled on desktop/mobile Chromium and Linux WebKit 2388;
these do not certify Safari/iOS behavior or guarantee full-speed execution.
The user subsequently confirmed that the automatic counter keeps counting in
their iOS Chrome setup. Browser/OS versions were not supplied; pause/resume,
other ROMs and this new addressing milestone are not yet device-confirmed.
A separate check with older WebKit 2083 rejects the missing timeline features,
leaves the automatic clock disabled, and successfully runs the checkpoint fallback.

Relevant specifications: [re-snapping after layout changes](https://www.w3.org/TR/css-scroll-snap-1/#re-snap)
defines snap retention when content moves. WebKit's [scroll-driven animation guide](https://webkit.org/blog/17101/a-guide-to-scroll-driven-animations-with-just-css/)
describes named timelines and scope. Their combination as CPU storage is an
experimental design validated by our state-transition tests, not a claim that
every browser must support arbitrary CSS feedback reliably.


## Register pairs and indirect addressing (build 07)

The CPU now implements 127 unprefixed opcodes. The 43 additions are `LD rr,d16`,
`INC/DEC rr` and `ADD HL,rr` for BC/DE/HL/SP; `LD SP,HL`; `JP HL`; loads/stores
between A and [BC]/[DE]/[HL+]/[HL-]; all register/[HL] byte transfers;
`LD [HL],d8`; and `INC/DEC [HL]`. Pair operations split a wrapped 16-bit result
into simultaneous high/low writes from the old state. SP is an independent
16-bit state word retained by every storage mode. Initial SP is zero, consistent
with our other zeroed registers rather than a boot-ROM register image.

The decoder separates immediate words from the effective data address. Its
memory bus selects a read value, write value and write-enable from the opcode.
Embedded ROM bytes can be read as data; only existing RAM C000–C03F and VRAM
8000–800F are writable. Reads outside those regions and the supplied ROM bytes
trap. Writes to ROM also trap, with no MBC behavior yet. A rejected access leaves
PC, registers, flags, memory and the instruction count unchanged while setting
fault. In particular, a failed [HL+] or [HL-] access does not update HL. This is
the experiment's explicit unmapped-access policy, not an emulation of the full
hardware memory map. Instruction fetch remains ROM-only.

The original tile image is now embedded after the cartridge's HALT instruction.
HL reads its 16 bytes with post-increment, DE writes them to VRAM, and B controls
the loop. This takes 84 instructions and halts at PC 010F. Python encodes the
ROM/data layout; it never performs the copy or generates its execution trace.

New ROM cases cover each indirect register transfer (including H/L aliasing),
word wrap, flag preservation/carries, post-update boundaries, ROM reads and
rejected writes, read-modify-write flags, and JP HL. A 344-instruction automatic
case fills all 64 RAM bytes through a pointer, then copies the last 16 backwards
to VRAM across bank swaps. A manual checkpoint case retains SP FEDC and HL
across the 128-step boundary. No new RAM capacity or stack operations are claimed:
At this stage PUSH/POP/CALL/RET, signed SP arithmetic and `LD [a16],SP`
were unimplemented; build 08 adds them.

Semantics reference: [RGBDS Game Boy instruction manual](https://github.com/gbdev/rgbds/blob/master/man/gbz80.7).
Instruction sizes were also checked against [gbdev's opcode data](https://github.com/gbdev/gb-opcodes/blob/master/Opcodes.json).


## Stack and subroutines (build 08)

The CPU implements 152 unprefixed opcodes. The 25 additions are PUSH/POP for
BC/DE/HL/AF; unconditional and NZ/Z/NC/C CALL/RET; conditional JP; ADD SP,e8;
LD HL,SP+e8; and LD [a16],SP. POP AF clears F's low nibble. Signed SP operations
clear Z/N and derive H/C from the low nibble/byte addition using the immediate's
unsigned byte, including when the signed displacement is negative.

Two adjacent memory lanes transfer words in a single instruction transition.
The low byte occupies the lower address. PUSH and CALL store at old SP-2/SP-1;
POP and RET read at old SP/SP+1. Addresses and SP wrap at 16 bits. CALL pushes
PC+3, and RET uses the actual word read from memory. Untaken conditional calls
and returns advance normally without reading, writing or validating the stack.

Both addresses must pass the existing memory policy before *any* state commits.
If either byte is unmapped or a write targets ROM, the instruction traps with no
partial write, SP change, register/flag change or PC/tick advancement. This is
an instruction-level diagnostic policy, not cycle-level bus fault emulation.
A valid RET to an unmapped instruction address does commit its pop, then faults
on the next fetch. RAM is still only C000–C03F and VRAM 8000–800F; there is no
special stack memory or automatic SP initialization. RST, RETI and interrupt
semantics remain absent. The ROM layout still starts at 0100, with no vectors.

Stack lab calls an outer subroutine four times. It saves BC, increments A,
calls an inner subroutine that increments A and clobbers BC, restores BC and
returns. Main checks the result and writes the success marker. It takes 52
instructions and restores SP to C040. The same embedded program is available
in all four modes. A separate test pauses the generic pipeline at 128 while
live stack frames remain in RAM, then verifies POP/RET after actual automatic
and manual bank transfers. Test fixtures also exercise independent byte-order
expectations, POP AF masking, taken/untaken conditions, SP arithmetic and
rejected partial transfers with page JavaScript disabled.

## ROM loading boundary

HTML's [`input type=file`](https://html.spec.whatwg.org/multipage/input.html#file-upload-state-(type=file))
can select a local file and submit it through a form. It does not expose its
binary contents as HTML attributes or CSS values. CSS
[`attr()`](https://drafts.csswg.org/css-values-5/#attr-notation) reads attributes,
not file bodies. The [File API](https://www.w3.org/TR/FileAPI/) supplies scripted
access to those bytes. Computational expressiveness does not provide this I/O.

A direct browser-only "Load ROM" feature would therefore need a small JS importer to encode
bytes for the CSS machine. Emulation could remain CSS, but the application
would no longer have a zero-JS runtime. Alternatively, a native HTML form could
upload the file to a converter that returns generated HTML/CSS, preserving a
script-free browser while introducing a server component. Build 09 implements this conversion approach as an offline command and a native
HTML form. The form is permitted only on converter routes; runtime scripts
remain forbidden. Offline conversion keeps the generated page self-contained.
Import alone would not make commercial ROMs run: instruction coverage, the
memory map, cartridge banking and hardware support are still incomplete.


## Offline and server conversion (build 09)

`tools/convert.py` is the shared converter. It validates byte count, cartridge
layout and practical CSS size, then feeds bytes to the existing generic CPU
builders. The input is never executed or translated into an execution trace.
All styles are inlined into one HTML document, with escaped metadata, a SHA-256
fingerprint, the conversion caveat and hardware limits. Imported programs show
HALTED, never the built-in diagnostic's TEST PASSED marker.

Imported ROM lookup now has an explicit base and range: full cartridges map file offsets
0000–7FFF; raw diagnostics map at 0100. The most frequent byte is encoded as the
lookup default and exceptions as address selectors. This preserves every byte,
including padding. Range checks distinguish mapped padding from an unmapped
fetch; RAM and VRAM still override only their separate mapped addresses. This
is data compression, independent of the program's execution path. It does not
add cartridge banking, interrupt vectors/RST semantics, a boot ROM or new RAM.
Small built-in cartridges retain their original direct lookup expressions:
their automatic-stage dependency graph stays unchanged and is timing-sensitive.
Imported cartridges use the bounded compact representation and may run slower.

`tools/server.py` accepts bounded multipart uploads or the generated page's
native reset form. It returns inline HTML or an attachment. Online Reset posts
an embedded base64 copy back for conversion; Run/Pause never call the server.
The download/CLI variant instead reloads its local file and has no server reset
form. No upload/session database, reusable artifact URL or cross-user cache is
created. The server has two bounded Gunicorn workers behind nginx; uploads and
temporary output use memory only in deployment. Filenames are display text,
never paths. Native forms use same-origin Referrer-Policy so browsers supply an
Origin header; cross-origin POSTs are rejected. All responses forbid scripts.

Tests cover original full-ROM execution, offset 0000, the second unbanked ROM
window, 7FFF, mapped zero padding, raw programs, continuing/trapping CPU state,
native form reset, download and offline file execution with page JS disabled.
Unit tests cover unsupported layouts, upload parsing/limits, metadata escaping,
no-overwrite CLI behavior and data preservation. See [usage and limits](CONVERTER.md).

## 8-bit ALU and independent conformance (build 10)

The base decoder now implements 228 opcodes. All ADD/ADC/SUB/SBC/AND/XOR/OR/CP
register, immediate and `[HL]` forms use a shared operand/result network. The
bitwise paths combine eight numeric bit extractions; Python emits expressions
but never evaluates a ROM program. Carry and half-carry use the old accumulator,
operand and input carry. CP changes only flags. Memory forms reuse the ordinary
read validation, so an unmapped operand traps without changing PC, flags or A.

DAA derives its correction from old A/N/H/C; subtraction uses only the H/C
corrections. It recomputes Z, preserves N, clears H and returns the adjusted C.
Accumulator rotates always clear Z, unlike the future CB-prefixed forms. CPL
preserves Z/C; SCF and CCF preserve Z and clear N/H. Semantics are checked against
[RGBDS's instruction reference](https://rgbds.gbdev.io/docs/gbz80.7) and external
expected-state fixtures described in [compatibility evidence](COMPATIBILITY.md).

`tools/conformance.py` emits independent one-instruction feed-forward cells
using the production `machine()` and `portable.storage()` generators. Each
cell's input ROM bytes and initial registers are numeric CSS data fixed before
loading. Expected results are never passed to the browser page. The tests read
state with page JavaScript disabled, covering both CSS calculation paths where
supported. The adapter relocates PC and `[HL]` memory for our restricted map;
it does not test bus cycles or the upstream suites' full ROM harnesses.

An original ALU lab exercises the new instructions through real program flow
and visible success/failure. Separate end-to-end programs validate flags across
automatic and manually copied storage banks. ROM conversion retains the same
size limits, privacy behavior and explicit external-conversion caveat.


## Build 11: CB decoding

The base decoder selects CB as one two-byte instruction. The second byte splits
into group, operation/bit index and register index. Shared CSS expressions
compute rotates, shifts, nibble swaps and bit masks; the generator never executes
those instructions. Register destinations use the old state, including H/L.

BIT leaves its operand unchanged and validates only readability. Other `[HL]`
forms require writable memory even for a no-op SET/RES. The common invalid-access
gate suppresses every state write on failure. The prefix also validates that its
second byte is mapped ROM, so a truncated raw upload cannot execute a synthetic
FF suffix. A CB instruction increments the instruction counter once; this is
still not a cycle-accurate bus model.

The conformance adapter retains upstream final memory for CB writes, with 32
vectors for each of 256 opcodes. Four groups keep browser test batches bounded.
The Bit lab and bank-boundary tests exercise the complete execution and storage
paths, including a CB memory instruction at slot 128.


## Build 12: restart vectors and high RAM

RST pushes old PC+1, low byte at old SP-2 and high byte at old SP-1, then jumps
to its fixed vector. Both stack lanes must be writable before any state commits.
LDH immediate and C-indexed forms address FF00 plus their unsigned operand.
Only FF80–FFFE is currently mapped there; I/O and IE still trap explicitly.

All 127 HRAM bytes join the ordinary memory state, including generic byte/word
loads, CB read-modify-write, stack accesses and both retention banks. The manual
banks store 1,770 bits each (3,542 inputs including commit/power); automatic
mode has 441 scroll cells. The complete-bank readiness condition includes every
new byte. Group/slot checkpoint selectors also cover the last HRAM bit.

The larger retained state and mapped-RAM fetches increase browser work. On
shared test runners, two automatic batches can take more than two seconds, and
manual stack-frame copying can exceed two minutes. Tests allow longer bounded
waits while retaining exact state and partial-copy isolation assertions. These
are correctness checks, not a game-speed benchmark.

Instruction fetch uses the same ROM/RAM mapping as data reads, so programs can
write and execute code in HRAM, the current work RAM window or VRAM. An explicit
validity gate checks exactly the instruction's one, two or three bytes before
retirement, even for an untaken conditional branch. This is essential because
FF is now a valid RST 38: the lookup's unmapped placeholder must not act as an
instruction. Missing bytes trap without changing PC, ticks, registers or memory.
This remains instruction-level behavior, without hardware bus-cycle timing.


## Build 13: interrupt control and instruction-boundary delivery

The CSS CPU retains IME, a one-instruction EI delay latch, a one-fetch HALT-bug
latch, IF and IE. This expands automatic storage to 225 words / 451 scroll cells
and each manual bank to 1,789 bits / 3,580 total inputs including commit/power.
IF is initialized to E0; writes retain low five bits and reads force the upper
three to one. IE retains eight bits but dispatch considers only the low five.

Pending requests are the low-five-bit intersection of IF and IE. With IME set,
the lowest set bit selects vector 40/48/50/58/60. A synthetic internal operation
uses the same atomic stack-write path to push current PC, clears the selected
IF bit and IME/delay, then jumps. It runs before fetching an instruction, even
if current PC is unmapped. It consumes one pipeline stage without incrementing
`ticks`; the 128-stage batch therefore retires at most 128 instructions.
The synthetic operation is not counted as a supported opcode.

DI cancels both IME and scheduled EI. EI schedules enable after the next retired
instruction; another EI does not postpone a previous enable. RETI enables at
retirement. Failed fetches/accesses leave these latches unchanged. Sleeping
HALT blocks retirement only while no enabled request is pending. With IME off
and a request already pending, HALT instead sets a one-use fetch latch. Opcode
fetch still reads PC, while operands, sequential PC and return-address math
use PC minus that latch. Interrupt entry also uses the adjusted return PC for
EI→HALT. Both paths consume the latch exactly once.

The automatic copy gate examines pending requests in the immutable source, so
a halted source with a request can still commit its resumed result. Tests seed
such states only before page load. There are no asynchronous hardware sources
yet. Interrupt entry remains atomic rather than five M-cycles; stack writes to
IE/IF do not reproduce the hardware's cycle-by-cycle cancellation races.


Continuous-counter inspection is expensive in Chromium: the same local probe
on 0.11 and 0.12 measured approximately ten seconds per running computed-style
read and twenty seconds for a native Pause input. Shared CI exceeded a fifteen-
second read deadline. Counter progress checks allow thirty seconds per read and
seven minutes for the repeated pause/resume scenario, preserving exact state,
no-inspection progress, and bounded-stall assertions. Finite interrupt programs
retain their shorter deadlines.


## Build 14: instruction-duration accounting

`tools/timing.py` emits `--duration` in T-cycles from the current opcode, flags
and CB operand kind. `--tcycles` adds that duration modulo 65,536 through the
same successful-transition gate as registers and PC. Interrupt entry adds 20
while `ticks` remains unchanged; HALT entry adds 4, then freezes until wakeup.
The counter records accepted CPU work, not wall time or a bus-level timeline.
Atomic fetch/transfer failures leave it unchanged. No Python executes a ROM.

This adds one 16-bit retained word: 226 state fields, 453 automatic scroll cells,
1,805 bits per manual bank and 3,612 native inputs including commit and power.
Every mode uses the same 16-bit cycle wrap. The complete-bank readiness
handshake includes the cycle word; partial manual copies cannot affect the
active result. The public Machine inspector exposes the count and its limits.

Existing SM83 fixtures now compare durations from their upstream M-state arrays.
A separate timing-only set retains one raw record per observed duration for all
242 non-HALT unprefixed instructions, including both conditional outcomes.
A third immutable ROM-byte slot lets those fixtures exercise 16-bit immediates.
Their operands are adapted to mapped addresses; expected cycle totals remain
outside the page. Original tests cover interrupt entry, HALT, traps, wraparound,
retention and the 24-instruction / 196-T-cycle diagnostic. Full bus ordering,
HALT idle clocks, register-write races and peripheral clocks remain future work.


## Build 15: timer circuitry and HALT waits

`tools/timer.py` emits six generic M-cycle lanes. Each lane advances the divider
by four T-cycles if selected by the current instruction's duration, computes a
selected-bit falling edge, updates TIMA or performs the previous lane's pending
reload, and accumulates a timer request. The current operation remains atomic;
these lanes are timer circuitry, not CPU bus micro-operations. Data reads use
the last active lane. Final-boundary writes apply DIV/TAC edge effects and
TIMA/TMA reload rules. IF acknowledgement precedes a timer request; explicit
CPU IF writes then win. See the compatibility report for the remaining races.

DIV's high byte is retained as FF04; `div-low` supplies the lower eight bits.
FF05–FF07 retain TIMA/TMA/TAC, with one `timer-reload` bit for the next M-cycle.
All generated phases are multiples of four; fixtures must use aligned seeds.
The `clocked` bit records accepted CPU or timer-only progress, so the startup
check can distinguish a working timer wait from a stalled scroll-storage bank.
These seven additional fields produce 233 state fields, 467 automatic scroll
cells, 1,847 bits per manual bank and 3,696 total native inputs.

Sleeping CPU state is unchanged during a timer-only lane, including `ticks`
and `tcycles`. Timer-enabled or reload-pending HALT sources remain eligible for
a complete automatic bank commit. Manual controls remain available while an
event can resume execution. The display says WAITING for that state. When no
live timer/reload or enabled request remains, HALT becomes quiescent and all
clocks stop. Faults and user Pause also freeze timer state. The original Timer
lab runs within one batch; the boundary fixture places HALT and overflow at
stage 128, then transfers the pending reload before servicing the timer.

Mooneye fixture assembly uses a strict whitelist, retains the original test
body, copies expected registers from upstream assertions and substitutes only
the result harness. Full CPU state, flag and duration conformance checks remain
separate; they have not been replaced by timer-only expectations.
