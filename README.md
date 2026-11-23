# DMGSS

A Game Boy emulator experiment written in **HTML and CSS**, with no runtime
JavaScript or WebAssembly. Python generates repetitive CSS at build time;
browser automation is used only for testing.

## Status

Early development. Not yet a general-purpose Game Boy emulator.
The current build executes original embedded ROMs on a CSS CPU supporting 243 unprefixed and all 256 CB-prefixed instructions with
16-bit register pairs, indirect addressing, stack/subroutines, the complete 8-bit ALU, decimal adjustment, arithmetic flags, branches and 64 bytes of work RAM plus 127 bytes of high RAM.
Power on to run it; the screen reports success or a CPU trap. Tile lab runs a
second original ROM that copies a four-shade tile from ROM data into 16 bytes of VRAM using pointers. Stack lab exercises nested calls and saved registers. The full
PPU, timers, hardware interrupt sources and game compatibility remain ahead.
See [the roadmap](docs/ROADMAP.md) for supported behavior and remaining work.

## Development

- Python 3.11+ and Node.js 22+ for build/test tooling.
- `python3 tools/build.py` generates the static site in `dist/`.
- `python3 -m http.server 8080 --directory dist` serves it locally.
- `python3 -m pip install -r requirements.txt` installs the local converter server.
- `npm ci && npx playwright install chromium webkit` installs browser test tooling.
- `npm test` runs browser tests with page JavaScript disabled.

Four execution modes share the same CPU:

- **Automatic continuation** (`/automatic/`): press Run once to keep executing
  through reusable CSS scroll-storage banks. Pause retains state; Reset clears it.
  Tested in Chromium and current Linux WebKit. Requires scroll timelines;
  the user confirmed its counter keeps advancing in iOS Chrome. Other features
  still need device checks. Counter, CPU check and Tile lab are included.
- **Compatible mode** (`/portable/`): runs up to 128 instructions in CSS, with
  reset and tile rendering. Tested in Chromium and Linux WebKit (including a
  build without CSS `if()`). The user also confirmed it works in iOS Chrome.
- **Manual checkpoints** (`/checkpoint/`): reusable HTML bit banks allow further
  128-instruction batches. Tap Save next bit for each changed bit, then Run next
  128. This is user-clocked copying, not automatic execution; iOS verification
  of this new mode is pending. State lasts until reset/navigation.
- **Streaming mode** (`/`): animated state storage for continuous execution,
  currently Chromium-only. It reports unsupported syntax or stalled startup.

None of these modes is game-ready. No commercial ROMs or Nintendo boot ROM are bundled.

## Workflow

Each milestone or fix gets a branch, pull request, checks and squash merge.
The public GitHub repository is `zdiemer/DMGSS`. Deployment uses the sibling
`selfhosted` repository's registry, Helm and Traefik conventions.

## Try the homelab build

[DMGSS](https://dmgss.zachd.duckdns.org) uses your existing Authelia login.
See [deployment instructions](docs/DEPLOYMENT.md). Power on to run the built-in
CPU diagnostic, or select Tile lab to watch VRAM fill. On iOS, try
[Compatible mode](https://dmgss.zachd.duckdns.org/portable/) and press Run;
it displays the final state immediately. The A/B/directional controls are not wired yet.

[Try automatic continuation](https://dmgss.zachd.duckdns.org/automatic/): press Run
once to keep incrementing RAM C000 beyond 128 instructions, without saving bits
or committing batches yourself. Pause keeps the last committed state. This new
mode needs a browser with working scroll timelines; use Compatible mode or
manual checkpoints if it reports a browser limit or stalled engine.

[Try manual checkpoints](https://dmgss.zachd.duckdns.org/checkpoint/): the counter
cartridge increments RAM C000 and continues beyond the first 128 instructions.
It usually takes several save taps per batch; programs changing lots of memory
can require hundreds. Keyboard: Tab to the focus link, Enter, then Space to save.

[Try Stack lab](https://dmgss.zachd.duckdns.org/automatic/stack/): nested subroutines
save and restore BC while computing a result, then report TEST PASSED.

[Load a ROM](https://dmgss.zachd.duckdns.org/convert/) through a native HTML form,
or convert offline:

```sh
python3 tools/convert.py demo.gb -o demo.html
python3 tools/convert.py demo.bin --format raw --mode automatic -o demo.html
```

**The caveat:** Python performs conversion outside the browser. It encodes ROM
bytes, never an execution trace. The resulting single HTML file runs the CPU in
HTML/CSS with no runtime scripts. Server uploads are not retained; use the offline
command to keep conversion local. Import does not imply game compatibility.
See [converter limits and usage](docs/CONVERTER.md).

[Try ALU lab](https://dmgss.zachd.duckdns.org/automatic/alu/): decimal arithmetic,
carry, bitwise operations and rotations. The CPU is checked against 15,328
independent cases from Mooneye and SingleStepTests. These are adapted CPU-state
checks, not whole-ROM passes; see [compatibility evidence](docs/COMPATIBILITY.md).

[Try Bit lab](https://dmgss.zachd.duckdns.org/automatic/bits/): all CB families,
including register operations and RAM/VRAM read-modify-write instructions.

[Try High RAM](https://dmgss.zachd.duckdns.org/automatic/high/): all restart
vectors, high-memory loads, stack returns and a routine written into RAM.

[Try Interrupts](https://dmgss.zachd.duckdns.org/automatic/interrupts/): software
requests exercise all five priority vectors, delayed EI, RETI and the HALT bug.
The Machine inspector now shows T-cycles for instructions and interrupt entry.
This 16-bit counter survives batch transfers and wraps at 65,536. Bus timing,
HALT idle time and hardware interrupt sources are still missing.
