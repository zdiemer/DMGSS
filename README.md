# DMGSS

A Game Boy emulator experiment written in **HTML and CSS**, with no runtime
JavaScript or WebAssembly. Python generates repetitive CSS at build time;
browser automation is used only for testing.

## Status

Early development. Not yet a general-purpose Game Boy emulator.
The current build executes an original embedded diagnostic ROM on an 84-opcode
CSS CPU with registers, arithmetic flags, branches and 64 bytes of writable RAM.
Power on to run it; the screen reports success or a CPU trap. Tile lab runs a
second original ROM that writes a four-shade tile into 16 bytes of VRAM. The full
PPU, timers, interrupts and game compatibility remain ahead.
See [the roadmap](docs/ROADMAP.md) for supported behavior and remaining work.

## Development

- Python 3.11+ and Node.js 22+ for build/test tooling.
- `python3 tools/build.py` generates the static site in `dist/`.
- `python3 -m http.server 8080 --directory dist` serves it locally.
- `npm ci && npx playwright install chromium webkit` installs browser test tooling.
- `npm test` runs browser tests with page JavaScript disabled.

Three execution modes share the same CPU:

- **Compatible mode** (`/portable/`): runs up to 128 instructions in CSS, with
  reset and tile rendering. Tested in Chromium and Linux WebKit (including a
  build without CSS `if()`). The user also confirmed it works in iOS Chrome.
- **Manual checkpoints** (`/checkpoint/`): reusable HTML bit banks allow further
  128-instruction batches. Tap Save next bit for each changed bit, then Run next
  128. This is user-clocked copying, not automatic execution; iOS verification
  of this new mode is pending. State lasts until reset/navigation.
- **Streaming mode** (`/`): animated state storage for continuous execution,
  currently Chromium-only. It reports unsupported syntax or stalled startup.

Neither mode is game-ready. No commercial ROMs or Nintendo boot ROM are bundled.

## Workflow

Each milestone or fix gets a branch, pull request, checks and squash merge.
The private GitHub repository is `zdiemer/DMGSS`. Deployment uses the sibling
`selfhosted` repository's registry, Helm and Traefik conventions.

## Try the homelab build

[DMGSS](https://dmgss.zachd.duckdns.org) uses your existing Authelia login.
See [deployment instructions](docs/DEPLOYMENT.md). Power on to run the built-in
CPU diagnostic, or select Tile lab to watch VRAM fill. On iOS, try
[Compatible mode](https://dmgss.zachd.duckdns.org/portable/) and press Run;
it displays the final state immediately. The A/B/directional controls are not wired yet.

[Try manual checkpoints](https://dmgss.zachd.duckdns.org/checkpoint/): the counter
cartridge increments RAM C000 and continues beyond the first 128 instructions.
It usually takes several save taps per batch; programs changing lots of memory
can require hundreds. Keyboard: Tab to the focus link, Enter, then Space to save.
