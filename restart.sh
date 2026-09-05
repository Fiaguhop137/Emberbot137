#!/bin/bash
set -e
export PATH=/usr/bin:/bin:/usr/sbin:/sbin
export XDG_RUNTIME_DIR=/run/user/1000
cd "$(dirname "$0")"
sleep 1
pkill -f "python3 /home/firebot/git/Emberbot137/emberbot137.py" || :
git sync || :
nohup python3 /home/firebot/git/Emberbot137/emberbot137.py > /home/firebot/git/Emberbot137/emberbot137.log 2>&1 &
