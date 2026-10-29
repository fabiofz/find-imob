#!/bin/bash

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

sudo mount -t drvfs G: /mnt/g

python3 teste.py

rm -rf script_teste/__pycache__
