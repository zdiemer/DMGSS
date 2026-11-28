"""Original VRAM lab: ROM bytes only; copies execute in the browser's CSS CPU."""
from cpu import tile_data


def video_rom():
    # Fill the last 16 VRAM bytes, cross a bank checkpoint, then copy them into
    # the visible tile. The viewer remains a memory inspector, not PPU scanout.
    code = [0x3E,0xE4,0xE0,0x47,0x21,0,0,0x11,0xF0,0x9F,0x06,16,
            0x2A,0x12,0x13,0x05,0x20,0xFA] + [0]*43
    code += [0x21,0xF0,0x9F,0x11,0,0x80,0x06,16,
             0x2A,0x12,0x13,0x05,0x20,0xFA,0x76]
    address = 256+len(code)
    code[5:7] = [address&255,address>>8]
    return code + tile_data()
