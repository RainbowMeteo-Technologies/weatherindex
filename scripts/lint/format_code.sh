#!/usr/bin/env bash
set -e

folders=(
    "metrics" 
    "tests"
    "tools"
)

for i in "${folders[@]}"
do
    echo "Formatting ${i}"
    autopep8 --in-place --aggressive --aggressive --recursive $i
done