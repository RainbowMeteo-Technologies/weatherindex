#!/usr/bin/env bash
set -e

export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/tools"
pytest tests/

