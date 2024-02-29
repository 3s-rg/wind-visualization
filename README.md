# A Web-based 3D Visualization Platform for High-Precision Urban Wind Models

## Requirements

Node.js `^18`, Python `^3.11`

## Environment Variables

Environment variables are stored in `.env.local`.
The variables describe some of the behavior of the application:

```conf
# describes if development or production settings should be used
# available options: "development" and "production"
APP_ENV="development"

# defines on which port the flask app server should listenin debug mode
# default is 6000
SERVER_PORT=8080

# directory of the processed data relative to the directory from which
# the server is started or an absolute path
DATA_DIR="./data/processed"

# defines on which port the frontend server should listen
VITE_PORT=8090

# defines on which url the frontend server can find the app server
# note that with firewalls or port forwarding, this can be a different port
# than defined in SERVER_PORT
VITE_SERVER_URL="http://localhost:6000"

# token to use Cesium Ion on the website
# get this from https://ion.cesium.com > Sign up > Access Tokens
VITE_CESIUM_ION_TOKEN="abcdefghijklmnop..."
```

## Getting Started

```bash
# Create venv
python -m venv .venv

# Activate venv
source .venv/bin/activate

# Install dependencies
python3 -m pip install -r requirements.txt
npm install

# Run server and client
npm run dev
```

## Ingest Datasets

Place new datasets inside `data/unprocessed/[dataset name]/`.
The dataset should contain a `meta.json` file with the following structure:

```json
{
  "utmHemisphere": "N",
  "utmZone": 33,
  "utmCorners": [
    [383900, 5818000],
    [385900, 5820000]
  ]
}
```

The `utmCorners` are the coordinates of the lower left and upper right corners of the dataset in UTM coordinates.
The `utmHemisphere` and `utmZone` are the UTM zone of the dataset.

The remaining `.xy` files will be ingested as data files.
File names are irrelevant.

To ingest the dataset, run the following command:

```bash
source .venv/bin/activate
python -m server.scripts.ingest_data ./data/unprocessed ./data/processed
```

This can take a while depending on the size of the dataset. Existing datasets will be skipped.

## Docker

For an easy prototype deployment, we recommend using Nginx for the frontend and just running the internal Flask server for the backend.
For a production deployment, a real WSGI server should be used.
We use `uWSGI` in Docker as an example, along with `nginx` serving the static frontend.

First, run the following command to build the frontend:

```bash
npm run build
```

Static files will land in the `dist` directory.

Run frontend and backend services with `docker compose`:

```bash
docker compose build
docker compose up
```

The site will then be available on `localhost:8000`.
