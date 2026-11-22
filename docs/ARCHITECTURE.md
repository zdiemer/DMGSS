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

84 unprefixed opcodes: NOP; HALT; register-to-register LD (excluding [HL]);
LD r8,d8; INC/DEC r8; ADD/SUB/CP d8; XOR A; JP a16; JR and all four JR
conditions; LD [a16],A and LD A,[a16]. Z/N/H/C are packed in the F register.
Instruction fetch reads embedded bytes at 0100. The initial registers are zero,
not a boot-ROM or post-boot register image. RAM is currently C000–C03F, plus a single tile at VRAM 8000–800F.

Unknown opcodes and unmapped data accesses trap without advancing PC. HALT
stops execution until reset (interrupt wakeup and the halt bug are not implemented).
The diagnostic performs arithmetic, a RAM roundtrip, comparison and a backwards
loop, then writes A5 to C002 on success. The UI derives success from that memory
byte; it does not set it itself. Inspector values are decimal.

This is instruction-level execution, not cycle-accurate emulation. There is no
PPU, timer, interrupt controller, stack, cartridge banking or audio yet.


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
fails so the support policy can be revisited. Indefinite iOS execution still requires
a portable state-storage design and validation on actual iOS devices.


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
certification. Physical iOS validation remains outstanding.
