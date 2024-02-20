import * as Cesium from "cesium";
import { colorScale } from "./color-scale";
import {
  HEIGHT_OFFSET,
  SIMPLIFIED_LINE_WIDTH,
  SIMPLIFIED_SCALE_FACTOR,
  WIND_LINE_ARROW,
  WIND_LINE_SCALE_FACTOR,
  WIND_LINE_WIDTH,
  WIND_SPEED_UPPER_CUTOFF,
} from "./constants";

/*
 * Converts a data point to a Cesium entity
 * Does not add the entity to the viewer
 */
function datapointToEntity(
  datapoint: Datapoint,
  palette: string,
  simplified = false
) {
  const [lat, lon, alt, u, v, w] = datapoint;

  const altAdjusted = alt + HEIGHT_OFFSET;

  const [red, green, blue, alpha] = mapWindSpeedToColor(palette, u, v, w);

  const color = Cesium.Color.fromBytes(red, green, blue, alpha);

  const start = Cesium.Cartesian3.fromDegrees(lon, lat, altAdjusted);

  const scaleFactor = simplified
    ? SIMPLIFIED_SCALE_FACTOR
    : WIND_LINE_SCALE_FACTOR;

  const endLat = lat + (v / 111111) * scaleFactor;

  const endLon =
    lon + ((u / 111111) * scaleFactor) / Math.cos((lat * Math.PI) / 180);

  const end = Cesium.Cartesian3.fromDegrees(endLon, endLat, altAdjusted);

  const material = WIND_LINE_ARROW
    ? new Cesium.PolylineArrowMaterialProperty(color)
    : color;

  const entity = new Cesium.Entity({
    polyline: {
      positions: [start, end],
      width: simplified ? SIMPLIFIED_LINE_WIDTH : WIND_LINE_WIDTH,
      material: material,
    },
  });

  return entity;
}

/*
 * Converts an array of data points to an array of Cesium entities
 * Does not add the entities to the viewer
 */
function datapointsToEntities(
  datapoints: Datapoint[],
  palette: string,
  simplified = false
) {
  return datapoints.map((datapoint) =>
    datapointToEntity(datapoint, palette, simplified)
  );
}

/*
 * Maps the given wind speed to a color
 */
function mapWindSpeedToColor(
  palette: string,
  u: number,
  v: number,
  w: number
): [number, number, number, number] {
  const magnitude = Math.sqrt(u * u + v * v + w * w);

  const clampedMagnitude = Math.min(magnitude, WIND_SPEED_UPPER_CUTOFF);

  const value = clampedMagnitude / WIND_SPEED_UPPER_CUTOFF;

  return [...colorScale(palette, value), 255];
}

/*
 * Converts a trixel to a Cesium polyline entity
 * Does not add the entity to the viewer
 */
export function trixelToPolylineEntity(
  trixel: Trixel,
  color: Cesium.Color
): Cesium.Entity {
  const [lat1, lon1] = trixel.vertices[0];
  const [lat2, lon2] = trixel.vertices[1];
  const [lat3, lon3] = trixel.vertices[2];

  const [p1, p2, p3] = Cesium.Cartesian3.fromDegreesArray([
    lon1,
    lat1,
    lon2,
    lat2,
    lon3,
    lat3,
  ]);

  const entity = new Cesium.Entity({
    polyline: {
      positions: [p1, p2, p2, p3, p3, p1],
      width: 1,
      material: color,
    },
  });

  return entity;
}

/*
 * Renders an array of data points into the given viewer
 * Returns an array of the entities that were added
 */
export function renderSimplified(
  viewer: Cesium.Viewer,
  data: Datapoint[],
  palette: string
) {
  const entities = datapointsToEntities(data, palette, true);

  entities.forEach((entity) => viewer.entities.add(entity));

  return entities;
}

/*
 * Renders an array of data points into the given viewer
 * Returns an array of the entities that were added
 */
export function renderDetailed(
  viewer: Cesium.Viewer,
  data: Datapoint[],
  sampleRate: number,
  palette: string
) {
  const entities: Cesium.Entity[] = [];
  const sampleRateInt = Math.round(1 / sampleRate);

  for (let i = 0; i < data.length; i += sampleRateInt) {
    const datapoint = data[i];
    const entity = datapointToEntity(datapoint, palette);
    entities.push(entity);
  }

  entities.forEach((entity) => viewer.entities.add(entity));

  return entities;
}
