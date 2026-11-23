# ROM conversion

[Open the loader](https://dmgss.zachd.duckdns.org/convert/) using the existing
homelab login. Select a file, its layout and execution mode, then choose
**Convert & run** or **Download HTML**. The original sample ROM linked in the
loader exercises nested subroutines; after Run it halts at 53 instructions,
with A=165 and SP=49216. It includes no Nintendo logo or boot ROM and is an
original CPU fixture, not a claim of physical cartridge compatibility.

## The caveat

Conversion uses Python outside the browser. It encodes ROM bytes as CSS data and
generates generic CPU stages. It never executes the ROM or precomputes a trace.
The generated page executes in HTML/CSS, with scripts and WebAssembly forbidden.
The complete application therefore includes an external conversion step; the
emulator's browser runtime remains HTML/CSS-only.

The browser form uploads your file to the server. Inputs and generated pages
are not retained: processing is request-local, with temporary generated assets
on tmpfs and cleanup after generation. No ROM bytes or filenames are put in
URLs or request logs. The generated HTML contains the encoded ROM; keep that in
mind when sharing it. Use offline conversion if the ROM should never be uploaded.

## Offline command

Python 3.11+ is sufficient; the converter itself has no third-party dependencies:

```sh
python3 tools/convert.py demo.gb -o demo.html
python3 tools/convert.py demo.bin --format raw --mode automatic -o demo.html
```

The output path must be new; existing files are never overwritten. Open the
single HTML file in a supported browser. No server, extra assets or network
requests are needed for execution. Its Reset link reloads the file. A mobile OS
may open downloaded HTML in a previewer instead of a full browser; use the
server's Convert & run option in that situation.

Modes: `portable` (default, up to 128 instructions), `automatic` (scroll-timeline
continuation), `checkpoint` (user-clocked bit saves), and `streaming` (Chromium
only). The generated file contains the selected mode only. Convert again to
choose another mode; fallback messages do not switch to an unrelated cartridge.

## Current limits

- `gb`: exactly 32,768 bytes mapped at 0000–7FFF. Header cartridge type, ROM size
  and RAM size must all be 00 (ROM ONLY, 32 KiB, no cartridge RAM). CGB-only ROMs
  are rejected. Logo and header checksums are not a boot/compatibility test and
  are not enforced. See [Pan Docs](https://gbdev.io/pandocs/The_Cartridge_Header.html).
- `raw`: 1–4,096 bytes, loaded at 0100. No header is interpreted.
- At most 1,024 bytes may differ from the file's most frequent byte. The rest
  remain mapped data; they are compressed as a CSS lookup default, not removed.
  Dense ROMs are rejected before generating an unwieldy stylesheet.
- Server requests are limited to 64 KiB including multipart/form overhead.
- PC starts at 0100; other registers including SP start at zero. No boot ROM or
  post-boot state is synthesized. The CPU still supports 228 unprefixed and 256 CB-prefixed instructions, only 64
  bytes of work RAM and one VRAM tile. Banking, full graphics, interrupts,
  timers, joypad and audio are unimplemented. Unknown instructions and unmapped
  accesses trap. HALTED means the program halted, not that a game is compatible.

The online result is also self-contained for execution. Reset resubmits its
embedded bytes for fresh conversion; Load another ROM returns to the picker.
Download HTML omits that server dependency. No per-instruction server calls,
server-side emulation, persisted sessions or JavaScript loader are involved.

## Run the service locally

```sh
python3 -m pip install -r requirements.txt
python3 tools/build.py
python3 -m gunicorn --chdir tools --bind 127.0.0.1:8080 --workers 2 --no-control-socket server:application
```

Open `/convert/`. For normal static-only preview, `python3 -m http.server` still
works for built-in cartridges, but it cannot handle conversion POSTs.
