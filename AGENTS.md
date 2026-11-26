# DMGSS agent instructions

Read the shared code-root AGENTS.md first. Work in the standalone DMGSS checkout,
never selfhosted's submodule. Keep this file and CLAUDE.md identical.

## Product contract

- Browser execution is HTML + CSS only: no scripts, event handlers, WASM,
  server-side emulation, precomputed execution traces or video pretending to run.
- Offline/server Python conversion and test-only JavaScript are allowed. ROM
  bytes may be encoded into generated HTML/CSS; disclose this conversion caveat.
  Never execute ROM instructions in the converter. CPU, memory and graphics transitions happen in CSS.
- Keep the Game Boy-inspired UI responsive, keyboard reachable and touch usable.
- Clearly label unsupported browsers and unimplemented hardware. Never claim
  game compatibility based on an animation or CPU-only diagnostic.
- Only include original or appropriately licensed ROMs/assets. Credit research.

## Delivery

- Use a feature branch and PR for each cohesive milestone/fix. Run relevant
  checks, squash merge, delete the branch, then update the local main branch.
- Test real state transitions with page JavaScript disabled: all modes in
  Chromium, and compatible/checkpoint/automatic modes in WebKit. Test mobile and desktop layouts.
  Unsupported opcodes must trap visibly. Keep the 128-step batch limit explicit;
  Linux WebKit coverage is not real-device iOS certification. Checkpoint mode
  requires native user input for each copied bit; never imply automatic storage.
  Preserve grouped checkpoint display queries; large direct index queries failed
  in Chromium when copying the stack near the end of RAM.
- Automatic mode uses scroll offsets and a complete-bank readiness handshake.
  Keep its source immutable during copies, commit HALT/fault before stopping,
  and round timeline readback explicitly. No timed copy assumption or test-driven
  state writes. Scope timelines above the animated reader. Preserve fallback
  modes and the startup progress check; iOS certification remains separate.
- Preserve independent conformance data, pins and license notices. Expected
  results must come from upstream, never the implementation under test. Label
  relocated single-instruction fixtures separately from whole-ROM passes.
  Only native browser inputs drive end-to-end execution; test fixtures may seed
  initial state at generation time, never through runtime state writes.
- Keep README concise; track capabilities and remaining work in docs/ROADMAP.md.
- Addressing uses old-state BC/DE/HL pairs and a separate 16-bit SP. A rejected
  data access must not update pointers, flags, memory, PC or ticks. ROM data is
  readable but not writable; retain explicit traps until the memory map expands.
- Word memory transfers validate both byte addresses before committing either.
  Untaken conditional calls/returns do not access the stack. POP AF masks the
  low nibble of F; signed SP arithmetic computes H/C from the unsigned low byte.
- CB instructions retire both bytes atomically. BIT is read-only; other memory
  forms validate writability even for no-op results. Truncated prefixes trap.
- Instruction fetch uses mapped ROM/RAM and validates every required byte.
  FF is RST 38, never a substitute for an unmapped fetch. HRAM ends at FFFE;
  Serial registers FF01–FF02, timer registers FF04–FF07, IF (FF0F) and IE (FFFF) are mapped; other I/O traps.
- EI takes effect after the following retired instruction; DI cancels the delay,
  RETI enables immediately, and interrupt entry clears IME/delay. Preserve both
  latches and the HALT bug across banks. Pending low IE/IF bits wake HALT even
  with IME off. The HALT bug suppresses one fetch increment, including immediate
  addressing and CALL/RST return addresses. EI→HALT dispatch returns to HALT.
- Interrupt entry precedes opcode fetch, validates both stack bytes atomically,
  and does not increment the retired-instruction counter. IF upper bits read as
  one; IE retains all eight bits, only low five participate in dispatch. Keep
  instruction-level entry distinct from missing bus timing and hardware sources.
- Keep instruction ticks separate from T-cycle accounting. Successful steps add
  opcode duration modulo 65,536; interrupt entry adds 20 without a tick. Failed
  accesses and sleeping/paused/faulted states preserve the cycle count. Retain
  it atomically in every bank. The divider includes timer-driven HALT idle clocks;
  the CPU-work counter excludes them. This is not full bus timing.
- Timer lanes advance in 4-T-cycle units, up to six per accepted CPU operation.
  DIV is the high divider byte; resets also clear its low byte. Preserve TAC's
  high read bits, DMG falling-edge glitches, the one-M-cycle reload latch and
  IF bit 2 requests. Data reads observe the final M-cycle; writes occur at the
  retirement boundary. Word transfers are still atomic, not bus-ordered.
- HALT waits continue while TAC is enabled, reload is pending, or an internal
  serial transfer is active, including with
  IME/IE off. With no timer/reload/internal serial transfer and no pending enabled interrupt, halt is
  quiescent and the experiment stops all clocks. Pause/fault/traps freeze timer
  state. Do not claim STOP/CGB, arbitrary T-phase or general bus-race accuracy.
- Keep timer state and the clock-progress latch in the complete-bank handshake.
  Startup detection must recognize timer progress even with zero instructions.
  Manual controls remain usable while HALT is waiting for a timer.
- Serial is disconnected DMG behavior: SC bits 1–6 read high, SB shifts MSB
  first with incoming ones, internal bits take 512 T-cycles, completion clears
  SC bit 7 and raises IF bit 3. External transfers never invent clock pulses.
  Each SC write resets the experiment's transfer phase/bit count; this is an
  explicit approximation, not DIV/serial alignment or active-write race accuracy.
- Clocked SB/SC reads precede final-boundary CPU writes. Timer and serial requests
  combine after IRQ acknowledgement; explicit IF writes win. Retain the partial
  byte, sub-bit phase and output log through the complete-bank handshake.
- Serial output records actual shifted-out bits only upon completion. Keep the
  log bounded to the latest 16 bytes, with exact hex and printable-text views;
  control bytes are marks, never HTML. Count wraps at 65,536 independently of
  log length. Imported ROMs never inherit TEST PASSED from output or RAM values.
- Run ./build.sh before ./upgrade.sh when image inputs change. Use a new image
  tag; keep Chart.yaml appVersion and values.yaml image.tag in sync.
- Converter uploads stay request-local; temporary generated files use tmpfs in
  deployment and are removed on completion. Keep size/complexity limits, escaped
  metadata, no-store responses, no runtime scripts, and no hidden ROM persistence.
  Test native upload/reset/download with JavaScript disabled, including file://
  execution. Imported ROMs must never inherit the built-in TEST PASSED signal.
- Secrets only through existing op:// references resolved at deploy time; never
  create values.local.yaml. Static deployment should need no application secret.
- Push app commits before moving the deployed selfhosted submodule pin.

- Imported dense ROMs use paged CSS selectors and exact 16-bit byte pairs.
  All bytes remain mapped data, including unreachable bytes and padding. Keep
  intermediates registered and non-inheriting so expressions stay local and bounded; share identical pages.
  ROM helpers are combinational, never retained CPU state. Preserve fetch/data
  range validation and RAM/I/O overrides at page, word and 16-bit wrap boundaries.
  The 32 KiB ROM-only and 4 KiB raw input bounds remain; density is not a limit.
  Small/direct lookup graphs stay unchanged. Do not imply cartridge banking or
  whole-ROM compatibility merely because a dense file can now be converted.
