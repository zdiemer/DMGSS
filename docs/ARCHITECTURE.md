# CSS machine

HTML is the fixed structure, CSS is the runtime, Python is code generation.
The generator emits declarations, never a precomputed sequence of machine states.

A four-phase CSS animation drives two alternating animation banks. The latch
phase copies the previously computed result to the stored bank. The execute
phase samples next-state expressions into the result bank. Paused animations
retain sampled values between phases. Typed integer properties resolve numeric
expressions before they are sampled. This unusual browser behavior is tested
with page JavaScript disabled; it is not a portable general-purpose CSS guarantee.

Power pauses both banks and the clock. Reset navigates to a fresh document.
Browser throttling can slow or skip wall-clock ticks: this is an experimental
instruction clock, not a hardware-accurate oscillator.

Research: [x86CSS](https://github.com/rebane2001/x86CSS) demonstrates autonomous
CSS CPU state storage and a style-query clock; [Jane Ori's CPU hack](https://dev.to/janeori/expert-css-the-cpu-hack-4ddj)
explores CSS feedback. DMGSS uses its own generator and machine implementation.
[Pan Docs](https://gbdev.io/pandocs/) is the hardware reference.

## SM83 subset (build 02)

84 unprefixed opcodes: NOP; HALT; register-to-register LD (excluding [HL]);
LD r8,d8; INC/DEC r8; ADD/SUB/CP d8; XOR A; JP a16; JR and all four JR
conditions; LD [a16],A and LD A,[a16]. Z/N/H/C are packed in the F register.
Instruction fetch reads embedded bytes at 0100. The initial registers are zero,
not a boot-ROM or post-boot register image. RAM is currently C000–C03F.

Unknown opcodes and unmapped data accesses trap without advancing PC. HALT
stops execution until reset (interrupt wakeup and the halt bug are not implemented).
The diagnostic performs arithmetic, a RAM roundtrip, comparison and a backwards
loop, then writes A5 to C002 on success. The UI derives success from that memory
byte; it does not set it itself. Inspector values are decimal.

This is instruction-level execution, not cycle-accurate emulation. There is no
PPU, timer, interrupt controller, stack, cartridge banking or audio yet.
