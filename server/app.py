import json
import os

import numpy as np
from dotenv import dotenv_values
from flask import Flask, jsonify, request
from flask_cors import CORS

from .logic.datasets import get_dataset_names, get_datasets_with_simplified_layers

from .logic.htm import (
    Halfspace,
    lat_lon_to_xyz,
    sphere_surface_radius_to_halfspace_distance,
)
from .logic.constants import DETAILED_DEPTH, MAX_RADIUS

app = Flask(__name__)
CORS(app)


@app.route("/health_check")
def index():
    return "OK"


@app.route("/datasets", methods=["GET"])
def datasets():
    return jsonify(get_datasets_with_simplified_layers())


@app.route("/simplified", methods=["GET"])
def simplified():
    """
    Returns a simplified dataset layer
    """

    dataset = request.args.get("dataset")
    layer = request.args.get("layer")

    if not dataset or not layer:
        return (
            jsonify({"error": "Dataset and layer parameters are required."}),
            400,
        )

    if dataset not in get_dataset_names():
        return (
            jsonify({"error": f"Dataset {dataset} does not exist."}),
            400,
        )

    server_dir = os.path.dirname(os.path.abspath(__file__))

    dataset_dir = os.path.join(server_dir, "data", "processed", dataset)

    meta_file = os.path.join(dataset_dir, "meta.json")

    with open(meta_file) as f:
        meta = json.load(f)

    layers = meta["simplifiedLayers"]

    layerNames = list(layers.keys())

    if layer not in layerNames:
        return (
            jsonify({"error": f"Layer {layer} does not exist."}),
            400,
        )

    data = np.load(os.path.join(dataset_dir, layers[layer]))

    return jsonify(data.tolist())


@app.route("/trixels-in-radius", methods=["GET"])
def trixels_in_halfspace():
    """
    Returns all trixels in a given radius (not the data points in the trixels)
    """

    lat = request.args.get("lat")
    lon = request.args.get("lon")
    radius = request.args.get("radius")

    if not lat or not lon or not radius:
        return (
            jsonify(
                {"error": "Latitude, longitude and radius parameters are required."}
            ),
            400,
        )

    try:
        lat = float(lat)
        lon = float(lon)
        radius = float(radius)
    except ValueError:
        return jsonify({"error": "Invalid latitude, longitude or radius values."}), 400

    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return (
            jsonify(
                {
                    "error": "Latitude must be between -90 and 90."
                    + " Longitude must be between -180 and 180."
                }
            ),
            400,
        )

    if radius < 0:
        return (
            jsonify({"error": "Radius must be greater than or equal to 0."}),
            400,
        )

    if radius > MAX_RADIUS:
        return (
            jsonify({"error": f"Radius must be less than or equal to {MAX_RADIUS}."}),
            400,
        )

    halfspace_vector = lat_lon_to_xyz(lat, lon)
    halfspace_distance = sphere_surface_radius_to_halfspace_distance(radius)
    halfspace = Halfspace(halfspace_vector, halfspace_distance)

    trixels = halfspace.get_all_expanded_trixels_to_depth(DETAILED_DEPTH)

    trixels_response = []

    for trixel in trixels:
        trixels_response.append(
            {
                "name": trixel.name,
                **trixel.lat_lon(),
            }
        )

    return jsonify(trixels_response)


@app.route("/detailed-by-trixel-names", methods=["POST"])
def detailed_by_trixel_names():
    """
    Returns all 3D data points for a given list of trixel names
    """

    json_body = request.json

    if not json_body:
        return (
            jsonify({"error": "JSON body is required."}),
            400,
        )

    trixel_names = json_body.get("trixels")

    if not trixel_names or not isinstance(trixel_names, list):
        return (
            jsonify({"error": "Trixels parameter is required and must be a list."}),
            400,
        )

    dataset = json_body.get("dataset")

    if not dataset:
        return (
            jsonify({"error": "Dataset parameter is required."}),
            400,
        )

    if dataset not in get_dataset_names():
        return (
            jsonify({"error": f"Dataset {dataset} does not exist."}),
            400,
        )

    server_dir = os.path.dirname(os.path.abspath(__file__))

    dataset_dir = os.path.join(server_dir, "data", "processed", dataset)

    data = {}

    for trixel_name in trixel_names:
        trixel_file = os.path.join(
            dataset_dir, trixel_name.replace("-", "/"), "data.npy"
        )

        if not os.path.exists(trixel_file):
            data[trixel_name] = []
        else:
            trixel_data = np.load(trixel_file)
            data[trixel_name] = trixel_data.tolist()

    return jsonify(data)


def read_env():
    """
    Reads environment variables from .env files and returns them as a dictionary
    """

    # collect env variables to determine app environment
    env_preflight = {
        **dotenv_values(".env.local"),
        **os.environ,
    }

    app_env = env_preflight.get("APP_ENV", "production")

    # merge env variables from current app environment
    env = {
        "APP_ENV": app_env,
        **dotenv_values(f".env.{app_env}"),
        **env_preflight,
    }

    return env


if __name__ == "__main__":
    """
    Main entry point for the server
    """

    env = read_env()

    print(f"APP_ENV: {env.get('APP_ENV')}")

    is_dev = env.get("APP_ENV") == "development"

    if is_dev:
        app.run(debug=is_dev, port=env.get("SERVER_PORT", 6000))
