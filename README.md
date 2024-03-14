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
  "coordinatesRelative": true,
  "utmCorners": [
    [383900, 5818000],
    [385900, 5820000]
  ]
}
```

The `utmCorners` are the coordinates of the lower left and upper right corners of the dataset in UTM coordinates.
The `utmHemisphere` and `utmZone` are the UTM zone of the dataset.
If `coordinatesRelative` is set to `true`, coordinates will be added (or subtracted) from `utmCorners`, i.e., you have coordinates relative to some central point.

The remaining `.xy` files will be ingested as data files.
File names are irrelevant.

To ingest the dataset, run the following command:

```bash
source .venv/bin/activate
make ingest
```

This can take a while depending on the size of the dataset.
Existing datasets will be skipped.
Note that we use Numba to optimize this process.
If you want to find out how to optimize this further, use `make profile` to generate a profile call graph of the ingest process (requires GraphViz).

## Docker

For an easy prototype deployment, we recommend using Nginx for the frontend and just running the internal Flask server for the backend.
For a production deployment, a real WSGI server should be used.
We use `uWSGI` in Docker as an example, along with `nginx` serving the static frontend.

Note that this will load the environment variables specified in `.env.local` into the compiled version.
Run frontend and backend services with `docker compose`:

```bash
docker compose build
docker compose up
```

The site will then be available on `localhost:8000`.

## Google Cloud Run

The project can also be deployed to Google Cloud Run using [OpenTofu](https://opentofu.org/).
We assume access to a Google Cloud project that has `Artifact Registry API` and `Cloud Run API` enabled (you can enable them on the GCP console or by deploying a service and watching out for error messages).
Further, make sure you have `gcloud`, `docker`, and `make` available.

First, configure the necessary variables in `gcloud.env`:

```conf
GCP_PROJECT_ID=opencitywind
GCP_REGION=eu-west10
```

First, execute `make login` to authenticate with Google Cloud.
Then, execute `make setup` to configure Tofu and Google Cloud.

Run `make deploy` to build container images and deploy the Cloud Run service.
You will see a URL at which you can access the service.

Data in `data/processed` will be automatically uploaded to a Cloud Storage Bucket called `ocw-data`.
You can manually upload data later with:

```sh
gsutil -m rsync -d -r data/processed gs://ocw-data
```

Note that the `-d` option removes all data at the destination that is not in the source, so please use with caution!
We do not use compression (`-J` option), as we upload mostly binary files.

If you want to remove the service, run `make destroy`.
