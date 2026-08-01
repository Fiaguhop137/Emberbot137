#!/bin/bash
cd "$(dirname "$0")"
sleep 1
git pull
nohup python3 bot.py > bot_runtime.log 2>&1 &
