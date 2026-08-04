#!/bin/bash
set -e
cd "$(dirname "$0")"
sleep 1
pkill -f "python3 emberbot137.py"
git sync || :
gnome-terminal --geometry=120x30 --title="Emberbot137 Console" -- python3 emberbot137.py &

