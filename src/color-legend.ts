import { colorScale } from "./color-scale";
import {
  LEGEND_HEIGHT,
  LEGEND_WIDTH,
  WIND_SPEED_LOWER_CUTOFF,
  WIND_SPEED_UPPER_CUTOFF,
} from "./constants";

/**
 * Renders a color legend for the given palette into the given selector
 * Palette must be one of "viridis", "jet", or "plasma"
 */
export function renderLegend(selector: string, palette: string) {
  const container = document.querySelector(selector);

  if (!container) {
    throw new Error(`No element found for selector ${selector}`);
  }

  container.innerHTML = "";

  const canvas = document.createElement("canvas");
  canvas.width = LEGEND_WIDTH;
  canvas.height = LEGEND_HEIGHT;

  const ctx = canvas.getContext("2d");

  if (!ctx) {
    throw new Error("Could not get canvas context");
  }

  for (let x = 0; x < LEGEND_WIDTH; x++) {
    const colorRgb = colorScale(palette, x / LEGEND_WIDTH);

    const color = `rgb(${colorRgb[0]}, ${colorRgb[1]}, ${colorRgb[2]})`;

    ctx.fillStyle = color;
    ctx.fillRect(x, 0, 1, LEGEND_HEIGHT);
  }

  const verticalOffset = 1;
  const horizontalPadding = 5;

  ctx.font = "16px Arial";
  ctx.fillStyle = "white";
  ctx.shadowColor = "black";
  ctx.shadowBlur = 2;
  ctx.textBaseline = "middle";
  ctx.strokeStyle = "black";
  ctx.lineWidth = 2;

  ctx.textAlign = "left";
  ctx.strokeText(
    `${WIND_SPEED_LOWER_CUTOFF}`,
    horizontalPadding,
    LEGEND_HEIGHT / 2 + verticalOffset
  );
  ctx.fillText(
    `${WIND_SPEED_LOWER_CUTOFF}`,
    horizontalPadding,
    LEGEND_HEIGHT / 2 + verticalOffset
  );

  ctx.textAlign = "right";
  ctx.strokeText(
    `${WIND_SPEED_UPPER_CUTOFF}`,
    LEGEND_WIDTH - horizontalPadding,
    LEGEND_HEIGHT / 2 + verticalOffset
  );
  ctx.fillText(
    `${WIND_SPEED_UPPER_CUTOFF}`,
    LEGEND_WIDTH - horizontalPadding,
    LEGEND_HEIGHT / 2 + verticalOffset
  );

  container.appendChild(canvas);
}
