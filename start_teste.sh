#!/bin/bash

python3 -m venv .venv
source .venv/bin/activate

sudo mount -t drvfs G: /mnt/g

python3 teste.py

rm -rf script_teste/__pycache__