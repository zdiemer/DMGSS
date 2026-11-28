# ROM conversion

[Open the loader](https://dmgss.zachd.duckdns.org/convert/) using the existing
homelab login. Select a file, its layout and execution mode, then choose
**Convert & run** or **Download HTML**. The original sample ROM linked in the
loader exercises nested subroutines; after Run it halts at 53 instructions,
with A=165 and SP=49216. It includes no Nintendo logo or boot ROM and is an
original CPU fixture, not a claim of physical cartridge compatibility.

The loader also offers an original **work RAM sample**. It checks both directions
of C000–DFFF and its E000–FDFF echo aliases and halts after **24 instructions with A=165**.
An original **MBC1 sample** calls bank 2, then reads bank 1 through zero-bank
translation. It halts after **13 instructions with A=17 and RAM C000=42**.

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
continuation), `checkpoint` (user-clocked bit saves), and `streaming` (one instruction per scroll commit). The generated file contains the selected mode only. Convert again to
choose another mode; fallback messages do not switch to an unrelated cartridge.

## Current limits

- `gb`: ROM ONLY (type 00) at 32 KiB, or MBC1 (type 01) at 32, 64 or
  128 KiB. ROM header size 00/01/02 must match the exact file length; RAM size
  must be 00. Larger ROMs, RAM/battery types and other controllers are rejected. CGB-only ROMs
  are rejected. Logo and header checksums are not a boot/compatibility test and
  are not enforced. See [Pan Docs](https://gbdev.io/pandocs/The_Cartridge_Header.html).
- `raw`: 1–4,096 bytes, loaded at 0100. No header is interpreted.
- Compatible, Automatic and Manual modes accept every byte density: all bytes
  in a valid-size file are encoded.
  Dense ROMs use paged CSS lookup; sparse files keep the smaller direct lookup.
  Generated HTML can be several MiB. Prefer Compatible or Automatic mode;
  Manual bit copying can be very slow with many distinct pages. Streaming
  accepts at most 1,024 bytes differing from the most common byte; larger
  lookup graphs failed in its former animation banks. The replacement scroll
  storage keeps this conservative cap pending separate dense-streaming validation.
  Worst-case 32 KiB files are checked against HTML budgets of 12 MiB (Compatible),
  24 MiB (Automatic) and 96 MiB (Manual). Full work RAM makes even small programs
  large documents; manual pages can be slow on memory-constrained devices.
  The 128 KiB MBC1 budgets are 32, 40 and 104 MiB respectively.
- Server requests are limited to 192 KiB including multipart/form overhead.
- PC starts at 0100; CPU registers including SP start at zero. IF reads E0, SC reads 7E and
  TAC reads F8 initially because their unused bits read as one; IE and IME are zero. No boot ROM or
  post-boot state is synthesized. The CPU still supports 243 unprefixed and 256 CB-prefixed instructions, 8 KiB
  of work RAM, 127 bytes of high RAM and one VRAM tile. DI/EI/RETI, software interrupt requests and the HALT bug are supported.
  The Machine inspector counts T-cycles modulo 65,536; bus timing is approximate and HALT idle
  clocks are excluded from that CPU-work counter. DIV/TIMA/TMA/TAC and timer
  interrupts, including HALT wakeup, are supported at M-cycle boundaries.
  Disconnected SB/SC transfers and a 16-byte serial output monitor are supported;
  a full byte needs multiple batches. Clock phase and bus-write timing remain approximate.
  LCDC starts off; STAT reads 84. LCDC/STAT/LY/LYC, VBlank and STAT requests
  use fixed-duration scanlines, including HALT waits. Pixel rendering, LCD
  startup quirks, STAT write glitches and VRAM/OAM bus restrictions are absent.
  Larger cartridge banking, cartridge RAM, full graphics, cable peers, joypad and audio are unimplemented. Unknown instructions and unmapped
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

The loader also offers an original **dense ROM sample**, containing a full 32 KiB
of varied data and a short diagnostic that checks scattered reads. On success
Machine inspector shows 31 instructions and A=165 (decimal); the program also
writes 165 to RAM C002. Imported
pages deliberately show HALTED rather than TEST PASSED. This is a lookup test,
not a whole-ROM compatibility suite or a game.

MBC1 starts with its five-bit ROM register at zero (effective bank 1). Writes
to 2000–3FFF change that register. Zero translation happens before masking to
the connected ROM address lines, so nonzero selections can map physical bank 0.
Other MBC1 control writes are accepted but have no observable effect for these
small cartridges without RAM. A000–BFFF remains an explicit unsupported-access
trap; open-bus behavior is not modeled. Each fetch/data lane uses the old bank,
and the next instruction sees a successful bank write. See [MBC1](https://gbdev.io/pandocs/MBC1.html).


BGP (FF47) is now available to imported ROMs, with an initial value of zero.
The tile viewer applies its background shade mappings. This does not add a
160×144 renderer or game compatibility; conversion still only encodes ROM data.
