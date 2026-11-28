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
  immutable; supported MBC1 control writes affect its bank register only; retain explicit traps until the memory map expands.
- Word memory transfers validate both byte addresses before committing either.
  Untaken conditional calls/returns do not access the stack. POP AF masks the
  low nibble of F; signed SP arithmetic computes H/C from the unsigned low byte.
- CB instructions retire both bytes atomically. BIT is read-only; other memory
  forms validate writability even for no-op results. Truncated prefixes trap.
- Instruction fetch uses mapped ROM/RAM and validates every required byte.
  FF is RST 38, never a substitute for an unmapped fetch. HRAM ends at FFFE;
  Serial registers FF01–FF02, timer registers FF04–FF07, IF (FF0F), IE (FFFF) and LCDC/STAT/LY/LYC plus BGP (FF47) are mapped; other I/O traps.
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
  serial transfer is active, or the LCD is enabled, including with
  IME/IE off. With no timer/reload/internal serial transfer/LCD and no pending enabled interrupt, halt is
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
  The ROM ONLY 32 KiB, MBC1 32–128 KiB without cartridge RAM, and 4 KiB raw bounds remain. Dense imports require
  Compatible, Automatic or Manual mode; reject dense Streaming conversions
  with a clear error. Its former animation banks did not initialize reliably;
  the scroll-storage replacement retains this cap pending dense-streaming coverage.
  Small/direct lookup graphs stay unchanged. Do not imply cartridge banking or
  whole-ROM compatibility merely because a dense file can now be converted.

- Work RAM is the full 8 KiB at C000–DFFF; E000–FDFF mirrors C000–DDFF.
  Canonicalize all five fetch/data bus lanes independently. PC, SP and pointers
  remain logical; DE00–DFFF has no echo. FE00/OAM is still unsupported.
  CPU storage uses 4,096 exact little-endian words. Keep byte semantics and atomic
  two-lane validation, including DFFF/E000 and FDFF/FE00 boundaries.
- Bounded stages decode on pipeline-read and commit on pipeline-execute. WRAM/VRAM
  writes select a 256-byte page before its words; all other words inherit.
  Full production state is mandatory in every mode. Single-step conformance
  fixtures retain their declared C000–C03F operand window to bound test cost;
  preserve upstream expectations and separate full-map retention tests.
- Automatic mode has 16,627 scroll cells and grouped, non-inheriting raw timeline
  readers. Disable snapping on the source bank and whenever copying is disabled.
  Dormant WRAM/VRAM cells may disappear only when source, destination and result all
  equal their initial word (zero encoded offset). Test reactivation and nonzero
  seeds. FFFE and IE remain separate; peripheral fields are never paired.
- Manual checkpoints use grouped native bit inputs, local numeric readers and
  a staged difference selector. Keep native pointer/keyboard behavior, source
  immutability during every bit save, and the 132,522-bit complete-bank check.
  Avoid inheriting unevaluated bit sums or thousands of raw animation values.
- Browser memory is a release constraint: run full-map probes in an isolated
  browser process/container with a hard memory limit, not beside the workspace
  agent. Keep explicit document budgets and converter tmpfs/worker headroom.
- Keep optional CSS if() RAM reads behind feature detection and the math
  fallback testable. Writes use page queries and 256 local typed result slots
  shared by every CPU stage. Separate slots for each bus lane prevent cross-page
  writes from aliasing. Avoid flat per-word query tables or eager per-word
  conditionals: both overwhelm Chromium. Native reads select a page before a
  word; range membership uses compact numeric gates in both decoders. Single-step
  fixtures disable read acceleration so both decoders remain independently checked.
- Register small reusable calculation slots, not every input bit or timeline.
  Inactive manual bits must update only the comparison UI. Keep native sibling
  selectors (no :has), local raw-bit resets and separate input/copy stylesheets
  so large selector tables remain within browser limits.
  Name the checkpoint selector container and target it explicitly from the
  grouped page/slot/commit queries. Chromium can cache hidden page 0 after
  accessibility reads beneath powered-off controls; query a stable ancestor.
  Preserve the controls' source-order reading-flow scope: Chromium otherwise
  stalls on Tab traversal to high-index bits. Test native keyboard saves and commit.

- Streaming shares Automatic scroll banks but commits one generic CPU stage at
  a time, using the native conditional decoder. Gate it on CSS if() and scroll
  timeline support; preserve the real-progress startup check and pause/reset.

- MBC1 support is type 01 only at 32/64/128 KiB, with exact header/length and
  no cartridge RAM. Retain the raw five-bit bank register (initial zero);
  translate zero to one before masking the physical bank number. Translate
  all fetch/data lanes independently; RAM/I/O overrides remain logical.
  The other control writes are no-ops for this wiring. Larger carts, RAM,
  MBC1M and other controllers are rejected; A000–BFFF still traps.
- Bank control writes commit only after complete access validation. For two
  lanes targeting the bank register, LD [nn],SP uses high-address data last;
  stack writes use low-address data last. This final-state ordering does not
  imply bus-cycle accuracy. Preserve bank selection through all storage modes.
- Pinned Mooneye MBC1 tables are independent expectations; do not regenerate
  them from the mapper. They establish bank-map results, not whole-ROM passes.

- LCD timing maps FF40/FF41/FF44/FF45, retaining all four registers plus internal
  line, nine-bit dot phase and the shared STAT signal. Fixed visible modes use
  80/172/204 dots; VBlank is lines 144–153. LY becomes zero at dot 4 of line 153
  without leaving mode 1. LCD enable starts immediately at line 0/mode 2;
  disable resets phase. LCDC starts off and STAT reads 84. These are documented
  approximations: no pixels, mode-3 stalls, startup quirks, STAT-write glitch,
  special mode-2 VBlank request or VRAM/OAM access restrictions yet.
- STAT requests only on a rising edge of its ORed enabled sources. Preserve
  that latch across every bank; clearing IF while it stays high cannot retrigger.
  Clocked read values must not depend on CPU write data. Merge LCD write-induced
  requests after clocked IF reads, then let explicit IF writes win. Enabled LCD
  timing keeps HALT alive even with IE/IME off; pause/fault/traps freeze it.

- BGP (FF47) retains all eight bits and resets to zero; built-in tile ROMs must
  initialize their own palette. Decode VRAM color IDs before mapping BGP shades;
  background ID 0 is opaque. Preserve palette state through every bank and
  atomic traps. The tile viewer shows committed memory independently of LCDC,
  not scanline output. OBJ/CGB palettes and mid-scanline effects remain absent.

- VRAM retains all 8 KiB at 8000–9FFF as 4,096 additional words, with byte
  fetch/data semantics and atomic two-lane validation. It has no echo alias.
  A000 cartridge RAM remains unmapped; VRAM is currently accessible regardless
  of LCD mode. Do not claim mode-3 restrictions or PPU rendering.
- Keep automatic readers to 64 words and manual readers/comparisons to 64/256
  words so full-state pages remain below browser DOM-depth limits. Manual input
  selectors use the named checkpoint-bank ancestor for bank phase; chunk each
  table into at most 65,536 selectors per sheet. Preserve unique reader classes
  per group so browsers do not match the full bit table at every reader. Test
  native saves and commits.
