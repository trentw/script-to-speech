// Canvas mock for vitest-axe
export const createCanvas = () => ({
  getContext: () => ({
    getImageData: () => ({ data: [] }),
    fillRect: () => {},
    drawImage: () => {},
  }),
})