import Color from "color";

type ColorScale = { position: number; rgb: [number, number, number] }[];

const scales: Record<string, ColorScale> = {
  viridis: [
    { position: 0, rgb: [68, 1, 84] },
    { position: 0.13, rgb: [71, 44, 122] },
    { position: 0.25, rgb: [59, 81, 139] },
    { position: 0.38, rgb: [44, 113, 142] },
    { position: 0.5, rgb: [33, 144, 141] },
    { position: 0.63, rgb: [39, 173, 129] },
    { position: 0.75, rgb: [92, 200, 99] },
    { position: 0.88, rgb: [170, 220, 50] },
    { position: 1, rgb: [253, 231, 37] },
  ],
  jet: [
    { position: 0, rgb: [0, 0, 131] },
    { position: 0.125, rgb: [0, 60, 170] },
    { position: 0.375, rgb: [5, 255, 255] },
    { position: 0.625, rgb: [255, 255, 0] },
    { position: 0.875, rgb: [250, 0, 0] },
    { position: 1, rgb: [128, 0, 0] },
  ],
  plasma: [
    { position: 0, rgb: [13, 8, 135] },
    { position: 0.13, rgb: [75, 3, 161] },
    { position: 0.25, rgb: [125, 3, 168] },
    { position: 0.38, rgb: [168, 34, 150] },
    { position: 0.5, rgb: [203, 70, 121] },
    { position: 0.63, rgb: [229, 107, 93] },
    { position: 0.75, rgb: [248, 148, 65] },
    { position: 0.88, rgb: [253, 195, 40] },
    { position: 1, rgb: [240, 249, 33] },
  ],
};

/**
 * Turn a value between 0 and 1 into an RGB color, using the given palette
 * Palette must be one of "viridis", "jet", or "plasma"
 */
export function colorScale(
  palette: keyof typeof scales,
  value: number
): [number, number, number] {
  const scale = scales[palette];

  const clamped = Math.max(0, Math.min(1, value));

  const rightIndex =
    scale.findIndex((color) => color.position > value) ?? scale.length - 1;
  const leftIndex = rightIndex - 1;

  const left = scale[leftIndex];
  const right = scale[rightIndex];

  const rightWeight =
    (clamped - left.position) / (right.position - left.position);

  const leftColor = Color.rgb(left.rgb);
  const rightColor = Color.rgb(right.rgb);

  const color = leftColor.mix(rightColor, rightWeight);

  return color.rgb().array() as [number, number, number];
}
