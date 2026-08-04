#!/bin/bash
set -e
cd "$(dirname "$0")"
sleep 1
pkill -f "python3 emberbot137.py" || :
git sync || :
nohup python3 emberbot137.py > emberbot137.log 2>&1 &
