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
- `python3 tools/build.py` generates the static site in `dist/` (once implemented).
- `python3 -m http.server 8080 --directory dist` serves it locally.
- `npm ci && npx playwright install chromium webkit` installs browser test tooling.
- `npm test` runs browser tests with page JavaScript disabled.

Use recent Chrome/Edge on desktop or Chrome on Android. **iPhone/iPad is not
supported, including Chrome on iOS**, which uses WebKit. A responsive layout
does not imply engine compatibility. The console reports missing CSS syntax or
a stalled startup instead of presenting a non-running CPU as active. No commercial ROMs or Nintendo boot ROM are bundled.

## Workflow

Each milestone or fix gets a branch, pull request, checks and squash merge.
The private GitHub repository is `zdiemer/DMGSS`. Deployment uses the sibling
`selfhosted` repository's registry, Helm and Traefik conventions.

## Try the homelab build

[DMGSS](https://dmgss.zachd.duckdns.org) uses your existing Authelia login.
See [deployment instructions](docs/DEPLOYMENT.md). Power on to run the built-in
CPU diagnostic, or select Tile lab to watch VRAM fill; reset reloads the cartridge. The A/B/directional controls are not wired yet.
