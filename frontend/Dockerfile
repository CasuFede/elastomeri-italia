FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --chown=node:node package.json package-lock.json ./
RUN chown node:node /app
USER node
RUN npm ci
