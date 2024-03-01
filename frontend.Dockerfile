FROM node:20.11-alpine as build

COPY package.json package-lock.json tsconfig.json vite.config.ts index.html ./
COPY src ./src

COPY .env.local .
ENV VITE_SERVER_URL=""

RUN npm install
RUN npm run build

FROM nginx:bookworm

EXPOSE 80
COPY --from=build dist /usr/share/nginx/html

# we place this in templates to replace the default.conf file
# we need to adapt the proxy_pass directive to point to the backend service
COPY <<"EOF" /etc/nginx/templates/default.conf.template
server {
    root /usr/share/nginx/html;
        index index.html;

        location / {
            try_files $uri $uri/ @proxy;
        }

        location @proxy {
            # app is the name of the backend service in the docker-compose file
            proxy_pass ${NGINX_BACKEND_SERVICE};
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
EOF
