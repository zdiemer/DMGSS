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

Two execution modes share the same CPU:

- **Compatible mode** (`/portable/`): runs up to 128 instructions in CSS, with
  reset and tile rendering. Tested in Chromium and Linux WebKit (including a
  build without CSS `if()`). Actual iPhone/iPad verification is still needed.
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
