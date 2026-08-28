# Build the SPA, then hand the static files to nginx through a shared volume.
# The runtime image carries no server of its own: nginx already terminates TLS
# and proxies /api, so a second web server would only add a hop.

FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM alpine:3.21
COPY --from=build /app/dist /dist

# Runs once per deploy: replaces whatever the previous release left in the
# volume that nginx serves, then exits.
CMD ["sh", "-c", "rm -rf /srv/* && cp -a /dist/. /srv/ && echo 'frontend assets published'"]
