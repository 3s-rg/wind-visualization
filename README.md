# A Web-based 3D Visualization Platform for High-Precision Urban Wind Models

## Requirements

Node.js `^18`, Python `^3.11`

## Getting Started

```bash
# Create .env.local (and fill out Cesium token)
cp .env.example .env.local

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

Place new datasets inside `server/data/unprocessed/[dataset name]/`.
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
python -m server.scripts.ingest_data
```

This can take a while depending on the size of the dataset. Existing datasets will be skipped.

## Deploy

For an easy prototype deployment, we recommend using Nginx for the frontend and just running the internal Flask server for the backend.
For a production deployment, a real WSGI server should be used.

Example Nginx config:

```nginx
server {
    server_name [your domain]

    root /[path to project]/dist;
    index index.html;

    location / {
        try_files $uri $uri/ @proxy;
    }

    location @proxy {
        proxy_pass http://127.0.0.1:[port];
        proxy_set_header Host $host;

        proxy_http_version                 1.1;
        proxy_cache_bypass                 $http_upgrade;

        # Proxy SSL
        proxy_ssl_server_name              on;

        # Proxy headers
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Proxy timeouts
        proxy_connect_timeout              60s;
        proxy_send_timeout                 60s;
        proxy_read_timeout                 60s;
    }

    listen [::]:80;
    listen 80;
}
```

Then run the following command to build the frontend:

```bash
npm run build
```

And run the following command to start the backend:

```bash
python -m server.app
```
