#!/usr/bin/env bash

folders=( 
    "metrics" 
    "tests" 
    "tools"
)
status=0

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

for i in "${folders[@]}"
do
    echo "Checking ${i}..."

	autopep8 --diff --exit-code --aggressive --aggressive --recursive $i

    ((status=status+$?))
done

if [ $status -eq 0 ]
then
    echo -e "${GREEN}Check passed${NC}"
    exit 0
else
    echo -e "\n${YELLOW}Check failed. Please use 'autopep8' formatter in your IDE or run script from './scripts/lint/format_code.sh'${NC}"
    exit 1
fi