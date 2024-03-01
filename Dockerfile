# https://greut.medium.com/minimal-python-deployment-on-docker-with-uwsgi-bc5aa89b3d35
# https://cloud.google.com/run/docs/tips/python#other_wsgi_servers

FROM python:3.11-slim

ARG SERVER_PORT=8000
EXPOSE ${SERVER_PORT}
ENV SERVER_PORT=${SERVER_PORT}

RUN apt-get update && \
    apt-get install --no-install-recommends --no-install-suggests -y \
    uwsgi \
    uwsgi-plugin-python3 \
    # build-essential \
    # python3-dev \
    && rm -rf /var/lib/apt/lists/*

# RUN pip install --no-cache-dir uwsgi
WORKDIR /usr/src/app
COPY requirements.txt .
RUN python3 -m venv venv
RUN ./venv/bin/pip install --no-cache-dir -r requirements.txt

COPY server .

COPY <<"EOF" entrypoint.sh
#!/bin/sh
echo "Data dir: ${DATA_DIR}"
exec uwsgi --http-socket :${SERVER_PORT:-8000} \
    -i \
    --plugin python3 \
    -H /usr/src/app/venv \
    --master \
    -s /tmp/app.sock \
    --manage-script-name \
    --mount /=app:app
EOF

RUN chmod +x entrypoint.sh
ENTRYPOINT [ "./entrypoint.sh" ]
