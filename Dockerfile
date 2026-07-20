FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/Dustin-a11y/kong-graph"
LABEL org.opencontainers.image.description="Classical knowledge graph memory for AI agents — 99.4% retrieval"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.version="1.3.0"

WORKDIR /app

RUN pip install --no-cache-dir kong-graph

ENV KONG_SIMILARITY_THRESHOLD=0.3
ENV KONG_DATA_DIR=/data

RUN mkdir -p /data

EXPOSE 8502

CMD ["python", "-m", "kong_graph", "--host", "0.0.0.0", "--port", "8502"]
