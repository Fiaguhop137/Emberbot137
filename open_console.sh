#!/bin/bash
cd "$(dirname "$0")"
sleep 1
pkill -f "python3 bot.py"
git pull
gnome-terminal --title="Emberbot137 Console" -- python3 bot.py &
