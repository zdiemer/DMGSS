# Implementation milestones

1. **Shipped:** repository hygiene, reproducible build/test tooling.
2. **Shipped:** responsive console shell, standalone CSS clock and state storage.
3. **Shipped (subset):** embedded original diagnostic ROM: instruction fetch/decode, registers,
   arithmetic/flags, branches, writable memory and visible results.
4. **Started:** writable VRAM and verified two-bitplane tile viewer. Still needed:
   tile maps, the 160×144 display, LCD registers and scanline timing.
5. Full SM83 CPU, stack, interrupts, timers and DMA, verified against test ROMs.
6. Joypad integration, sprites, scrolling, cartridge banking and game testing.

Audio, ROM uploads and persistent saves require separate feasibility research
under the HTML/CSS-only runtime constraint. No full-speed promise.


Browser portability: **shipped bounded compatible mode**, with 128 generic CSS
instruction stages, both original cartridges and reset. Verified on Chromium and
Linux WebKit, including an older build without CSS `if()`. The user confirmed
Compatible mode on iOS Chrome. Streaming mode retains its explicit
startup diagnostics. See [the architecture](ARCHITECTURE.md#bounded-compatible-mode-build-04).


**Shipped experimental manual checkpoints:** two reusable native input banks
continue in 128-instruction batches, with user taps to save changed bits and
commit each batch. Tests cover continuation beyond 1,000 instructions. Automatic
WebKit retention, practical game speed, and iOS validation of checkpoint mode
remain open; the manual workflow is not a substitute for those milestones.
