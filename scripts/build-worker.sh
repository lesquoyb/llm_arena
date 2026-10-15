#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
export DOCKER_CONFIG="$(pwd)/.arena/docker-config"
mkdir -p "$DOCKER_CONFIG"
CONTEXT=.arena/docker-build
mkdir -p "$CONTEXT"
if [ ! -f "$CONTEXT/base-image.txt" ]; then
  docker pull debian:trixie-slim
  docker image inspect debian:trixie-slim --format '{{index .RepoDigests 0}}' > "$CONTEXT/base-image.txt"
fi
if [ ! -d "$CONTEXT/jdk" ]; then cp -a .arena/tools/jdk-25 "$CONTEXT/jdk"; fi
{
  printf 'FROM %s\n' "$(cat "$CONTEXT/base-image.txt")"
  printf '%s\n' 'COPY jdk /opt/jdk' 'RUN chmod -R a+rX /opt/jdk' 'ENTRYPOINT ["/opt/jdk/bin/java"]'
} > "$CONTEXT/Dockerfile"
docker build -t llm-arena-worker:local "$CONTEXT"
docker image inspect llm-arena-worker:local --format '{{.Id}}' > .arena/worker-image.txt
printf '%s\n' 'Use ARENA_WORKER_BACKEND=docker and ARENA_WORKER_IMAGE from .arena/worker-image.txt.'
