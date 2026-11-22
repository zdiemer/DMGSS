# Implementation milestones

1. **Shipped:** repository hygiene, reproducible build/test tooling.
2. **Shipped:** responsive console shell, standalone CSS clock and state storage.
3. Embedded original diagnostic ROM: instruction fetch/decode, registers,
   arithmetic/flags, branches, writable memory and visible results.
4. Tile-based 160×144 display, VRAM and LCD registers.
5. Full SM83 CPU, stack, interrupts, timers and DMA, verified against test ROMs.
6. Joypad integration, sprites, scrolling, cartridge banking and game testing.

Audio, ROM uploads and persistent saves require separate feasibility research
under the HTML/CSS-only runtime constraint. No full-speed promise.
