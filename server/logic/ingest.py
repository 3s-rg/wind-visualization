import glob
import itertools
import json
import os
import sys
import typing
import numpy as np
import utm

import tqdm

from .constants import INGEST_MAX_DEPTH, INGEST_MIN_DEPTH, SIMPLIFIED_DEPTH
from .htm import (
    find_trixel_from_lat_lon,
    find_trixel_from_name,
    lat_lon_to_xyz,
    xyz_to_lat_lon,
)


class Dataset:
    def __init__(
        self,
        name: str,
        unprocessed_path: str,
        processed_path: str,
        utm_zone: int,
        utm_hemisphere: str,
        utm_corner_min_x: int,
        utm_corner_min_y: int,
        utm_corner_max_x: int,
        utm_corner_max_y: int,
        layers: typing.List[str],
    ):
        self.name = name
        self.unprocessed_path = unprocessed_path
        self.processed_path = processed_path
        self.utm_zone = utm_zone
        self.utm_hemisphere = utm_hemisphere
        self.utm_corner_min_x = utm_corner_min_x
        self.utm_corner_min_y = utm_corner_min_y
        self.utm_corner_max_x = utm_corner_max_x
        self.utm_corner_max_y = utm_corner_max_y
        self.layers = layers

    def serialize(self) -> typing.Dict[str, typing.Any]:
        return {
            "name": self.name,
            "unprocessed_path": self.unprocessed_path,
            "processed_path": self.processed_path,
            "utm_zone": self.utm_zone,
            "utm_hemisphere": self.utm_hemisphere,
            "utm_corner_min_x": self.utm_corner_min_x,
            "utm_corner_min_y": self.utm_corner_min_y,
            "utm_corner_max_x": self.utm_corner_max_x,
            "utm_corner_max_y": self.utm_corner_max_y,
            "layers": self.layers,
        }

    def __str__(self) -> str:
        x_delta = self.utm_corner_max_x - self.utm_corner_min_x
        y_delta = self.utm_corner_max_y - self.utm_corner_min_y
        area = x_delta * y_delta
        return f"{self.name} ({len(self.layers)} layers, {area} m^2)"


class Mapping:
    def __init__(
        self,
        min_x: int,
        min_y: int,
        max_x: int,
        max_y: int,
        mapping: typing.List[typing.List[str]],
    ):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        self.mapping = mapping

    def get_total_entries(self) -> int:
        return sum(len(row) for row in self.mapping)

    def get_trixel_name(self, x: int, y: int) -> str:
        return self.mapping[y - self.min_y][x - self.min_x]


def get_ingestable_datasets(
    unprocessed_dir: str, processed_dir: str
) -> typing.List[Dataset]:
    """
    Returns a list of ingestable datasets (i.e. datasets that have not yet been processed)
    """

    datasets = []

    for f in os.scandir(unprocessed_dir):
        if not f.is_dir():
            continue

        processed_path = os.path.join(processed_dir, f.name)

        if os.path.isdir(processed_path):
            print(f"Skipping {f.name} because a processed version already exists")
            continue

        meta_path = os.path.join(f.path, "meta.json")

        if not os.path.isfile(meta_path):
            print(f"Skipping {f.name} because meta.json is missing")
            continue

        with open(meta_path) as meta_file:
            meta = json.load(meta_file)

        if "utmHemisphere" not in meta:
            print(f"Skipping {f.name} because utmHemisphere is missing from meta.json")
            continue

        if "utmZone" not in meta:
            print(f"Skipping {f.name} because utmZone is missing from meta.json")
            continue

        if "utmCorners" not in meta:
            print(f"Skipping {f.name} because utmCorners is missing from meta.json")
            continue

        if (
            len(meta["utmCorners"]) != 2
            or not all(len(corner) == 2 for corner in meta["utmCorners"])
            or not all(
                isinstance(n, (int, float))
                for corner in meta["utmCorners"]
                for n in corner
            )
        ):
            print(f"Skipping {f.name} because utmCorners is not a 2x2 array of numbers")
            continue

        min_x = min(corner[0] for corner in meta["utmCorners"])
        max_x = max(corner[0] for corner in meta["utmCorners"])
        min_y = min(corner[1] for corner in meta["utmCorners"])
        max_y = max(corner[1] for corner in meta["utmCorners"])

        if min_x == max_x or min_y == max_y:
            print(f"Skipping {f.name} because utmCorners do not form a rectangle")
            continue

        layers = glob.glob(f"{f.path}/*.xy")
        layers.sort()

        if len(layers) == 0:
            print(f"Skipping {f.name} because no .xy layers were found")
            continue

        dataset = Dataset(
            name=f.name,
            unprocessed_path=f.path,
            processed_path=processed_path,
            utm_zone=meta["utmZone"],
            utm_hemisphere=meta["utmHemisphere"],
            utm_corner_min_x=min_x,
            utm_corner_min_y=min_y,
            utm_corner_max_x=max_x,
            utm_corner_max_y=max_y,
            layers=layers,
        )

        print(f"Found {dataset}")

        datasets.append(dataset)

    datasets.sort(key=lambda d: d.name)

    return datasets


def parse_layer_lines(
    layer_path: str,
) -> typing.List[typing.Tuple[int, int, int, float, float, float]]:
    """
    Parses a layer file and returns a list of tuples of the form (x, y, z, u, v, w)
    """

    with open(layer_path, "r") as f:
        lines = f.readlines()

    print(f"Read {len(lines)} lines")

    lines = [line.strip().split() for line in lines]
    lines = [
        (int(x), int(y), int(z), float(u), float(v), float(w))
        for x, y, z, u, v, w in lines
    ]

    print(f"Parsed {len(lines)} data points")

    return lines


def get_layer_min_max_xy(layer_path: str) -> typing.Tuple[int, int, int, int]:
    """
    Returns the min/max x/y values for a layer
    """

    layer_filename = os.path.basename(layer_path)

    print(f"Scanning layer {layer_filename} for min/max x/y")

    lines = parse_layer_lines(layer_path)

    min_x = min([line[0] for line in lines])
    max_x = max([line[0] for line in lines])
    min_y = min([line[1] for line in lines])
    max_y = max([line[1] for line in lines])
    min_z = min([line[2] for line in lines])
    max_z = max([line[2] for line in lines])

    assert min_z == max_z, "z_min != z_max, this is not a 2D slice"

    return min_x, max_x, min_y, max_y


def get_dataset_min_max_xy(dataset: Dataset) -> typing.Tuple[int, int, int, int]:
    """
    Returns the min/max x/y values for a dataset
    """

    print(f"Scanning dataset {dataset.name} for min/max x/y")

    min_x = sys.maxsize
    max_x = -sys.maxsize
    min_y = sys.maxsize
    max_y = -sys.maxsize

    for layer_path in dataset.layers:
        layer_min_x, layer_max_x, layer_min_y, layer_max_y = get_layer_min_max_xy(
            layer_path
        )

        min_x = min(min_x, layer_min_x)
        max_x = max(max_x, layer_max_x)
        min_y = min(min_y, layer_min_y)
        max_y = max(max_y, layer_max_y)

    print(f"Dataset min/max x/y: ({min_x}, {min_y}) to ({max_x}, {max_y})")

    return min_x, max_x, min_y, max_y


def build_utm_to_htm_mapping(
    dataset: Dataset, min_x: int, min_y: int, max_x: int, max_y: int
) -> Mapping:
    """
    Builds a mapping from UTM coordinates to HTM trixels for a dataset
    """

    print(f"Building UTM to HTM mapping for dataset {dataset.name}")

    utm_center_x = int((dataset.utm_corner_min_x + dataset.utm_corner_max_x) / 2)
    utm_center_y = int((dataset.utm_corner_min_y + dataset.utm_corner_max_y) / 2)

    mapping = [[] for _ in range(max_y - min_y + 1)]

    prev_trixel = None
    cache_hits = 0

    t = tqdm.tqdm(
        itertools.product(range(min_y, max_y + 1), range(min_x, max_x + 1)),
        total=(max_y - min_y + 1) * (max_x - min_x + 1),
    )

    for i, (y, x) in enumerate(t):
        if i % 1000 == 0:
            t.set_postfix(
                cache_hit_rate=f"{cache_hits / (i + 1) * 100:.2f}%",
            )

        utm_x = utm_center_x + x
        utm_y = utm_center_y + y

        lat, lon = utm.to_latlon(utm_x, utm_y, dataset.utm_zone, dataset.utm_hemisphere)

        if prev_trixel is not None and prev_trixel.contains(*lat_lon_to_xyz(lat, lon)):
            mapping[y - min_y].append(prev_trixel.name)
            cache_hits += 1
            continue

        trixel = find_trixel_from_lat_lon(lat, lon, INGEST_MAX_DEPTH)

        prev_trixel = trixel

        mapping[y - min_y].append(trixel.name)

    return Mapping(min_x, min_y, max_x, max_y, mapping)


def parse_layer_to_trixels(
    dataset: Dataset,
    layer_path: str,
    mapping: Mapping,
) -> typing.Dict[str, typing.List[typing.List[float]]]:
    """
    Parses a layer file and returns a dictionary of trixel names to lists of points, using the given mapping
    """

    layer_filename = os.path.basename(layer_path)

    print(f"Processing layer {layer_filename}")

    trixels = {}

    lines = parse_layer_lines(layer_path)

    print(f"Mapping {len(lines)} data points to trixels")

    utm_center_x = int((dataset.utm_corner_min_x + dataset.utm_corner_max_x) / 2)
    utm_center_y = int((dataset.utm_corner_min_y + dataset.utm_corner_max_y) / 2)

    t = tqdm.tqdm(lines)
    for line_index, line in enumerate(t):
        x, y, z, u, v, w = line

        utm_x = utm_center_x + x
        utm_y = utm_center_y + y

        lat, lon = utm.to_latlon(utm_x, utm_y, dataset.utm_zone, dataset.utm_hemisphere)

        htm_trixel_name = mapping.get_trixel_name(x, y)

        if htm_trixel_name not in trixels:
            trixels[htm_trixel_name] = []

        trixels[htm_trixel_name].append([lat, lon, z, u, v, w])

    return trixels


def backfill_trixels(
    dataset: Dataset, saved_trixels: typing.Set[str]
) -> typing.Dict[int, typing.List[str]]:
    """
    Backfills trixels from the saved depth to the ingest min depth
    """

    saved_trixels_list = list(saved_trixels)

    saved_depth = saved_trixels_list[0].count("-") + 1

    assert all(
        trixel.count("-") + 1 == saved_depth for trixel in saved_trixels_list
    ), "Not all saved trixels have the same depth"

    print(f"Backfilling trixels from depth {saved_depth} to depth {INGEST_MIN_DEPTH}")

    trixels_by_depth = {
        saved_depth: saved_trixels_list,
    }

    prev_trixels_list = saved_trixels_list
    for depth in range(saved_depth - 1, INGEST_MIN_DEPTH - 1, -1):
        print(f"Backfilling trixels at depth {depth}")

        next_trixels = set()

        t = tqdm.tqdm(prev_trixels_list)

        for trixel_name in t:
            trixel_dirs = trixel_name.replace("-", "/")
            trixel_file = os.path.join(dataset.processed_path, trixel_dirs, "data.npy")

            parent_trixel_name = "-".join(trixel_name.split("-")[:-1])
            parent_trixel_dirs = parent_trixel_name.replace("-", "/")
            parent_trixel_file = os.path.join(
                dataset.processed_path, parent_trixel_dirs, "data.npy"
            )

            trixel_data = np.load(trixel_file)

            if os.path.exists(parent_trixel_file):
                parent_trixel_data = np.load(parent_trixel_file)
                trixel_data = np.concatenate((parent_trixel_data, trixel_data))

            np.save(parent_trixel_file, trixel_data)

            next_trixels.add(parent_trixel_name)

        prev_trixels_list = list(next_trixels)

        trixels_by_depth[depth] = prev_trixels_list

        print(f"Backfilled {len(prev_trixels_list)} trixels")

    return trixels_by_depth


def generate_simplified_layers(
    dataset: Dataset, trixels_by_depth: typing.Dict[int, typing.List[str]]
) -> typing.List[int]:
    """
    Generates simplified layers for a dataset
    """

    print(f"Generating simplified version for dataset {dataset.name}")

    trixels = trixels_by_depth[SIMPLIFIED_DEPTH]

    simplifiedLayers: typing.Dict[int, typing.List[typing.List[float]]] = {}

    t = tqdm.tqdm(trixels)

    for trixel_name in t:
        trixel = find_trixel_from_name(trixel_name)
        mid_lat, mid_lon = xyz_to_lat_lon(*trixel.get_midpoint())

        trixel_dirs = trixel_name.replace("-", "/")
        trixel_file = os.path.join(dataset.processed_path, trixel_dirs, "data.npy")
        trixel_data = np.load(trixel_file)

        pointsByAltitude: typing.Dict[int, typing.List[typing.List[float]]] = {}

        for point in trixel_data:
            x, y, z, u, v, w = point

            z = round(z)

            if z not in pointsByAltitude:
                pointsByAltitude[z] = []

            pointsByAltitude[z].append([u, v, w])

        for altitude, points in pointsByAltitude.items():
            if altitude not in simplifiedLayers:
                simplifiedLayers[altitude] = []

            simplifiedLayers[altitude].append(
                [mid_lat, mid_lon, altitude, *np.average(points, axis=0)]
            )

    trixel_simplified_dir = os.path.join(
        dataset.processed_path,
        "simplified",
    )

    os.makedirs(trixel_simplified_dir, exist_ok=True)

    for altitude, points in simplifiedLayers.items():
        simplified_file = os.path.join(trixel_simplified_dir, f"{altitude}.npy")

        np.save(simplified_file, points)

    return list(simplifiedLayers.keys())


def write_meta(
    dataset: Dataset,
    trixels_by_depth: typing.Dict[int, typing.List[str]],
    simplified_layers: typing.List[int],
):
    """
    Writes a meta.json file for a dataset
    """

    print(f"Writing meta.json for dataset {dataset.name}")

    meta = {
        "utmZone": dataset.utm_zone,
        "utmHemisphere": dataset.utm_hemisphere,
        "utmCorners": [
            [dataset.utm_corner_min_x, dataset.utm_corner_min_y],
            [dataset.utm_corner_max_x, dataset.utm_corner_max_y],
        ],
        "trixelsByDepth": {
            depth: [
                {
                    "name": trixel_name,
                    "data": os.path.join(trixel_name.replace("-", "/"), "data.npy"),
                }
                for trixel_name in trixels
            ]
            for depth, trixels in trixels_by_depth.items()
        },
        "simplifiedLayers": {
            altitude: os.path.join("simplified", f"{altitude}.npy")
            for altitude in simplified_layers
        },
    }

    meta_path = os.path.join(dataset.processed_path, "meta.json")

    with open(meta_path, "w") as meta_file:
        json.dump(meta, meta_file, indent=2)


def ingest_dataset(dataset: Dataset):
    """
    Ingests a dataset - main entry point
    """

    min_x, max_x, min_y, max_y = get_dataset_min_max_xy(dataset)

    print(f"Dataset UTM area: ({min_x}, {min_y}) to ({max_x}, {max_y})")

    mapping = build_utm_to_htm_mapping(dataset, min_x, min_y, max_x, max_y)

    print(
        f"Built UTM to HTM mapping with {mapping.get_total_entries()} entries for dataset {dataset.name}"
    )

    os.makedirs(dataset.processed_path)

    saved_trixels = set()

    for layer_path in dataset.layers:
        layer_trixels = parse_layer_to_trixels(
            dataset,
            layer_path,
            mapping,
        )

        layer_filename = os.path.basename(layer_path)

        print(f"Saving trixels for layer {layer_filename}")

        t = tqdm.tqdm(layer_trixels.items())

        for trixel_name, trixel_data in t:
            trixel_dirs = trixel_name.replace("-", "/")

            trixel_dir = os.path.join(dataset.processed_path, trixel_dirs)
            trixel_file = os.path.join(trixel_dir, "data.npy")

            os.makedirs(trixel_dir, exist_ok=True)

            if os.path.exists(trixel_file):
                existing_data = np.load(trixel_file)
                trixel_data = np.concatenate((existing_data, trixel_data))

            np.save(trixel_file, trixel_data)

            saved_trixels.add(trixel_name)

    trixels_by_depth = backfill_trixels(dataset, saved_trixels)

    simplified_layers = generate_simplified_layers(dataset, trixels_by_depth)

    write_meta(dataset, trixels_by_depth, simplified_layers)
