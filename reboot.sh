#!/bin/bash
pkill -f "python3 /home/firebot/git/Emberbot137/pyrenigma.py"
while pgrep -f "python3 /home/firebot/git/Emberbot137/pyrenigma.py" >/dev/null; do
    sleep 0.1
done
nohup python3 /home/firebot/git/Emberbot137/pyrenigma.py > /home/firebot/git/Emberbot137/pyrenigma.log 2>&1 &
