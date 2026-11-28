// Read-only inspection with page JavaScript disabled. Work/video RAM is stored in
// little-endian 16-bit words; decoding observations never changes browser state.
function readStyles(elements, keys) {
  return (Array.isArray(elements) ? elements : [elements]).map(el => {
    const style = getComputedStyle(el);
    return Object.fromEntries(keys.map(key => {
      const address = /^m\d+$/.test(key) ? Number(key.slice(1)) : -1;
      if ((address >= 0xC000 && address < 0xE000) || (address >= 0x8000 && address < 0xA000)) {
        const raw = style.getPropertyValue((address < 0xA000 ? '--vram' : '--wram') + (address & ~1));
        const word = Number(raw);
        if (!raw || !Number.isInteger(word) || word < 0 || word > 65535) throw new Error(`Invalid RAM word at ${address}: ${raw}`);
        return [key, Math.floor(word / (address % 2 ? 256 : 1)) % 256];
      }
      return [key, Number(style.getPropertyValue('--' + key))];
    }));
  });
}
async function readState(page, keys, selector = '.machine') {
  const states = await page.locator(selector).evaluate(readStyles, keys);
  if (states.length !== 1) throw new Error(`Expected one state at ${selector}, got ${states.length}`);
  return states[0];
}
module.exports = {readState, readStyles};
