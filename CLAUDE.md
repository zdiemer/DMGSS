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
- Keep README concise; track capabilities and remaining work in docs/ROADMAP.md.
- Addressing uses old-state BC/DE/HL pairs and a separate 16-bit SP. A rejected
  data access must not update pointers, flags, memory, PC or ticks. ROM data is
  readable but not writable; retain explicit traps until the memory map expands.
- Word memory transfers validate both byte addresses before committing either.
  Untaken conditional calls/returns do not access the stack. POP AF masks the
  low nibble of F; signed SP arithmetic computes H/C from the unsigned low byte.
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
