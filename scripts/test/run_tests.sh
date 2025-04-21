#!/usr/bin/env bash
set -e

export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
