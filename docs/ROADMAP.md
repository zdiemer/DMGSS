# Implementation milestones

1. **Shipped:** repository hygiene, reproducible build/test tooling.
2. **Shipped:** responsive console shell, standalone CSS clock and state storage.
3. **Shipped (subset):** embedded original diagnostic ROM: instruction fetch/decode, registers,
   arithmetic/flags, branches, writable memory and visible results.
   **Addressing milestone:** 127 opcodes, BC/DE/HL/SP word operations, indirect
   byte loads/stores, HL post-increment/decrement, and readable embedded ROM data.
   Tile lab now runs a pointer-based copy loop.
   **Stack milestone:** 152 opcodes, PUSH/POP, CALL/RET (including conditions),
   conditional JP, signed SP arithmetic and two-byte SP stores. Stack lab runs
   nested subroutines.
   **ALU milestone:** 228 base opcodes, complete 8-bit ALU, accumulator rotates,
   DAA and flag controls.
   **CB milestone:** all 256 prefixed operations, atomic two-byte retirement,
   BIT read-only access and RAM/VRAM modification. Independent coverage now
   includes 14,848 upstream cases.
   **High RAM milestone:** all restart vectors and LDH forms, all 127 HRAM
   bytes, executable mapped RAM, and atomic instruction-fetch validation.
   Coverage now includes 15,232 independent cases.
   Next: interrupt state and delivery, HALT behavior and hardware registers. See [external-test status](COMPATIBILITY.md).
4. **Started:** writable VRAM and verified two-bitplane tile viewer. Still needed:
   tile maps, the 160×144 display, LCD registers and scanline timing.
5. Full SM83 CPU, restart vectors, interrupts, timers and DMA, verified against test ROMs.
6. Joypad integration, sprites, scrolling, cartridge banking and game testing.

Audio and persistent saves require separate feasibility research. HTML file
inputs cannot expose ROM bytes to CSS: local import needs a JS loader or an
external conversion step. **Shipped:** offline Python conversion plus a native
HTML upload/download form. Both generate a self-contained HTML/CSS page for
small test programs or unbanked 32 KiB ROMs, subject to a CSS complexity limit.
The converter never executes the program; importing does not imply game
compatibility. See [the converter](CONVERTER.md). No full-speed promise.


Browser portability: **shipped bounded compatible mode**, with 128 generic CSS
instruction stages, both original cartridges and reset. Verified on Chromium and
Linux WebKit, including an older build without CSS `if()`. The user confirmed
Compatible mode on iOS Chrome. Streaming mode retains its explicit
startup diagnostics. See [the architecture](ARCHITECTURE.md#bounded-compatible-mode-build-04).


**Shipped experimental manual checkpoints:** two reusable native input banks
continue in 128-instruction batches, with user taps to save changed bits and
commit each batch. Tests cover continuation beyond 1,000 instructions. This mode
remains available for browsers without the scroll timelines used below.

**Shipped experimental automatic continuation:** two scroll-offset banks retain
CPU state across reusable 128-instruction batches, with no further input after
Run. Chromium and current Linux WebKit tests cover ongoing execution, pause,
reset, branches, retained registers/VRAM, HALT, traps and bookkeeping wraparound.
The user confirmed the automatic counter keeps advancing in their iOS Chrome
setup. Other features, pause/resume and broader device coverage remain unverified
on actual iOS. Practical game speed remains open; this is not a complete
Game Boy emulator. See [automatic storage](ARCHITECTURE.md#automatic-scroll-storage-build-06).
