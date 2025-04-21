#!/usr/bin/env bash
set -e

source .versions
export METRICS_DOCKER_VERSION=${METRICS_DOCKER_VERSION}
export PYTHONPATH="${PYTHONPATH}:$(pwd)"


python3 ./scripts/test/check_version.py
