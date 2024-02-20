import "modern-normalize/modern-normalize.css";
import "./style.css";

import * as Cesium from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import { Pane } from "tweakpane";
import { renderLegend } from "./color-legend";
import {
  CAMERA_DETAILED_ALTITUDE_THRESHOLD,
  CAMERA_JUMP_DETAILED_ALTITUDE,
  CAMERA_JUMP_SIMPLIFIED_ALTITUDE,
  CAMERA_PERCENTAGE_CHANGED_THRESHOLD,
  DEFAULT_PALETTE,
  HOME_HEIGHT,
  HOME_LATITUDE,
  HOME_LONGITUDE,
  TRIXELS_DEFAULT_RADIUS,
  TRIXELS_MAX_RADIUS,
  TRIXELS_MIN_RADIUS,
  TRIXELS_STEP_RADIUS,
  WIND_LINE_SAMPLING_RATE,
} from "./constants";
import {
  fetchDatasets,
  fetchDetailedByTrixelNames,
  fetchSimplified,
  fetchTrixelsInRadius,
} from "./fetching";
import {
  renderDetailed,
  renderSimplified,
  trixelToPolylineEntity,
} from "./rendering";

/*
 * Entry point for the application
 */
async function run() {
  console.log("run() triggered", performance.now());

  // Initialize Cesium

  Cesium.Ion.defaultAccessToken = import.meta.env.VITE_CESIUM_ION_TOKEN;

  const viewer = new Cesium.Viewer("cesium", {
    terrainProvider: await Cesium.createWorldTerrainAsync(),
    skyBox: false,
    // baseLayerPicker: false,
    sceneModePicker: false,
    navigationHelpButton: false,
    animation: false,
    timeline: false,
    fullscreenButton: false,
  });

  viewer.scene.debugShowFramesPerSecond = true;

  function setHomeView() {
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(
        HOME_LONGITUDE,
        HOME_LATITUDE,
        HOME_HEIGHT
      ),
      orientation: {
        heading: Cesium.Math.toRadians(0),
        pitch: Cesium.Math.toRadians(-90),
        roll: Cesium.Math.toRadians(0),
      },
    });
  }

  setHomeView();

  viewer.homeButton.viewModel.command.beforeExecute.addEventListener((e) => {
    e.cancel = true;
    setHomeView();
  });

  const osmBuildings = await Cesium.createOsmBuildingsAsync();
  viewer.scene.primitives.add(osmBuildings);

  const scene = viewer.scene;
  const camera = scene.camera;

  // Red dot for debugging

  const redDot = viewer.entities.add({
    position: Cesium.Cartesian3.ZERO,
    point: {
      pixelSize: 5,
      color: Cesium.Color.RED,
      outlineColor: Cesium.Color.BLACK,
      outlineWidth: 1,
    },
  });

  // Main state

  let detailedMode = false;

  let fetchingSimplified = false;
  let simplifiedEntities: Cesium.Entity[] = [];
  let simplifiedEntitiesRendered = false;

  let fetchingDetailed = false;
  const detailedEntitiesByTrixelName: Record<string, Cesium.Entity[]> = {};

  let fetchingTrixels = false;
  let trixels: Trixel[] = [];
  let trixelsEntities: Cesium.Entity[] = [];

  const datasets = await fetchDatasets();

  const firstDataset = Object.keys(datasets)[0];

  // Helper functions

  function clearSimplified() {
    simplifiedEntities.forEach((entity) => viewer.entities.remove(entity));
    simplifiedEntities = [];
    simplifiedEntitiesRendered = false;
  }

  function clearDetailed() {
    for (const trixelName in detailedEntitiesByTrixelName) {
      detailedEntitiesByTrixelName[trixelName].forEach((entity) =>
        viewer.entities.remove(entity)
      );

      delete detailedEntitiesByTrixelName[trixelName];
    }
  }

  function clearAllDatapoints() {
    clearSimplified();
    clearDetailed();
  }

  // Tweakpane State

  interface ParamsInterface {
    dataset: string;
    layer: string;
    showBuildings: boolean;
    altitude: number;
    radius: number;
    palette: string;
  }

  const params: ParamsInterface = {
    dataset: firstDataset,
    layer: datasets[firstDataset][0],
    showBuildings: true,
    altitude: HOME_HEIGHT,
    radius: TRIXELS_DEFAULT_RADIUS,
    palette: DEFAULT_PALETTE,
  };

  // Color legend

  renderLegend("#legend", params.palette);

  // Tweakpane UI

  const pane = new Pane({
    container: document.querySelector("#tweakpane") as HTMLElement,
    title: "Wind Visualization",
  });

  const bindingDataset = pane.addBinding(params, "dataset", {
    label: "Dataset",
    options: Object.keys(datasets).reduce((acc, dataset) => {
      acc[dataset] = dataset;
      return acc;
    }, {} as Record<string, string>),
  });

  bindingDataset.on("change", async () => {
    params.layer = datasets[params.dataset][0];

    clearAllDatapoints();

    handleCamera();
  });

  const bindingLayer = pane.addBinding(params, "layer", {
    label: "Layer",
    options: datasets[params.dataset].sort().reduce((acc, layer) => {
      acc[layer] = layer;
      return acc;
    }, {} as Record<string, string>),
  });

  bindingLayer.on("change", async () => {
    clearSimplified();

    handleCamera();
  });

  const bindingShowBuildings = pane.addBinding(params, "showBuildings", {
    label: "Show Buildings",
  });

  bindingShowBuildings.on("change", (e) => {
    if (e.value) {
      osmBuildings.show = true;
    } else {
      osmBuildings.show = false;
    }
  });

  pane.addBinding(params, "altitude", {
    readonly: true,
    view: "graph",
    min: 0,
    max: 2_000,
    label: "Altitude",
  });

  const buttonJumpSimplified = pane.addButton({
    title: "Simplified View (2D)",
  });

  buttonJumpSimplified.on("click", () => {
    const cameraCartographic = camera.positionCartographic;

    camera.flyTo({
      destination: Cesium.Cartesian3.fromRadians(
        cameraCartographic.longitude,
        cameraCartographic.latitude,
        CAMERA_JUMP_SIMPLIFIED_ALTITUDE
      ),
      duration: 1,
    });
  });

  const buttonJumpDetailed = pane.addButton({
    title: "Detailed View (3D)",
  });

  buttonJumpDetailed.on("click", () => {
    const cameraCartographic = camera.positionCartographic;

    camera.flyTo({
      destination: Cesium.Cartesian3.fromRadians(
        cameraCartographic.longitude,
        cameraCartographic.latitude,
        CAMERA_JUMP_DETAILED_ALTITUDE
      ),
      duration: 1,
    });
  });

  pane.addBinding(params, "radius", {
    min: TRIXELS_MIN_RADIUS,
    max: TRIXELS_MAX_RADIUS,
    step: TRIXELS_STEP_RADIUS,
    label: "Radius",
  });

  const bindingPalette = pane.addBinding(params, "palette", {
    label: "Palette",
    options: {
      plasma: "plasma",
      viridis: "viridis",
      jet: "jet",
    },
  });

  bindingPalette.on("change", () => {
    renderLegend("#legend", params.palette);

    clearAllDatapoints();

    handleCamera();
  });

  // Main update loop

  async function handleCamera() {
    // For debugging, set window.freezeCamera = true
    if ("freezeCamera" in window && window.freezeCamera) {
      return;
    }

    console.log("handleCamera() triggered", performance.now());

    const cameraPosition = camera.positionWC;
    const ellipsoid = scene.globe.ellipsoid;

    const cameraCartographic = camera.positionCartographic;

    const cameraLatitude = Cesium.Math.toDegrees(cameraCartographic.latitude);
    const cameraLongitude = Cesium.Math.toDegrees(cameraCartographic.longitude);
    const cameraAltitude = cameraCartographic.height;

    params.altitude = cameraAltitude;

    // Find the intersection of the camera ray with the globe

    const ray = new Cesium.Ray(cameraPosition, camera.directionWC);
    const intersection = scene.globe.pick(ray, scene);

    let rayLatitude = cameraLatitude;
    let rayLongitude = cameraLongitude;

    // Update the red dot

    if (intersection) {
      redDot.position = new Cesium.ConstantPositionProperty(intersection);

      const intersectionCartographic =
        ellipsoid.cartesianToCartographic(intersection);

      rayLatitude = Cesium.Math.toDegrees(intersectionCartographic.latitude);
      rayLongitude = Cesium.Math.toDegrees(intersectionCartographic.longitude);
    }

    if (cameraAltitude <= CAMERA_DETAILED_ALTITUDE_THRESHOLD) {
      if (!detailedMode) {
        console.log("switching to detailed", performance.now());

        detailedMode = true;
      }
    } else {
      if (detailedMode) {
        console.log("switching to simplified", performance.now());

        detailedMode = false;
      }
    }

    // Fetch and render trixel shapes (not the actual data points)

    if (!fetchingTrixels) {
      fetchingTrixels = true;

      fetchTrixelsInRadius(rayLatitude, rayLongitude, params.radius).then(
        (data) => {
          trixels = data;

          trixelsEntities.forEach((entity) => viewer.entities.remove(entity));

          trixelsEntities = data.map((trixel) => {
            return trixelToPolylineEntity(
              trixel,
              Cesium.Color.fromBytes(255, 255, 255, 32)
            );
          });

          trixelsEntities.forEach((entity) => viewer.entities.add(entity));

          fetchingTrixels = false;
        }
      );
    }

    // Detailed == 3D, Simplified == 2D

    if (detailedMode) {
      if (simplifiedEntitiesRendered) {
        simplifiedEntities.forEach((entity) => viewer.entities.remove(entity));
        simplifiedEntitiesRendered = false;
      }

      // Fetch and render new 3D data points, remove old irrelevant ones

      if (!fetchingDetailed) {
        fetchingDetailed = true;

        const currentTrixelNames = trixels.map((trixel) => trixel.name);

        const trixelNamesToFetch = currentTrixelNames.filter(
          (trixelName) => !detailedEntitiesByTrixelName[trixelName]
        );

        const trixelNamesToRemove = Object.keys(
          detailedEntitiesByTrixelName
        ).filter((trixelName) => !currentTrixelNames.includes(trixelName));

        console.log({
          trixelNamesToFetch,
          trixelNamesToRemove,
        });

        for (const trixelName of trixelNamesToRemove) {
          detailedEntitiesByTrixelName[trixelName].forEach((entity) =>
            viewer.entities.remove(entity)
          );
          delete detailedEntitiesByTrixelName[trixelName];
        }

        const trixelData = await fetchDetailedByTrixelNames(
          params.dataset,
          trixelNamesToFetch
        );

        for (const trixelName in trixelData) {
          const datapoints = trixelData[trixelName];

          const entities = renderDetailed(
            viewer,
            datapoints,
            WIND_LINE_SAMPLING_RATE,
            params.palette
          );

          detailedEntitiesByTrixelName[trixelName] = entities;
        }

        console.log("renderDetailed() done", performance.now());

        console.log({ detailedEntitiesByTrixelName });

        fetchingDetailed = false;
      }
    } else {
      if (Object.keys(detailedEntitiesByTrixelName).length > 0) {
        clearDetailed();
      }

      // Fetch and render simplified data points, only fetch once and then reuse

      if (simplifiedEntities.length === 0 && !fetchingSimplified) {
        fetchingSimplified = true;

        const simplifiedData = await fetchSimplified(
          params.dataset,
          params.layer
        );

        simplifiedEntities = renderSimplified(
          viewer,
          simplifiedData,
          params.palette
        );
        simplifiedEntitiesRendered = true;
        fetchingSimplified = false;

        console.log("renderSimplified() done", performance.now());
      } else if (simplifiedEntities.length > 0 && !simplifiedEntitiesRendered) {
        simplifiedEntities.forEach((entity) => viewer.entities.add(entity));
        simplifiedEntitiesRendered = true;
      }
    }
  }

  // Handle camera changes

  camera.changed.addEventListener(handleCamera);
  camera.percentageChanged = CAMERA_PERCENTAGE_CHANGED_THRESHOLD;
  handleCamera();
}

run();
