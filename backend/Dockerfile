FROM node:22-bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | env CARGO_DIST_FORCE_INSTALL_DIR="/usr/local/bin" sh

ENV UV_PYTHON_INSTALL_DIR=/opt/python
RUN uv python install 3.13 && chmod -R a+rx /opt/python

WORKDIR /app

RUN chown -R node:node /app
USER node

COPY --chown=node:node pyproject.toml uv.lock ./
RUN uv sync

COPY --chown=node:node . .

EXPOSE 8000
CMD ["uv", "run", "pywrangler", "dev", "--ip", "0.0.0.0", "--port", "8000"]
