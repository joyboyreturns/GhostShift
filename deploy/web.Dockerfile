FROM node:22.22.3-slim AS build
WORKDIR /build
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build
FROM caddy:2.11.7-alpine
COPY --from=build /build/dist /srv
COPY deploy/Caddyfile /etc/caddy/Caddyfile
