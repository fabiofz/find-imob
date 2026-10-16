#!/bin/bash

python3 -m venv .venv
source .venv/bin/activate

sudo mount -t drvfs G: /mnt/g

python3 runner.py

rm -rf scripts/__pycache__
rm -rf utils/__pycache__