#!/bin/bash
pkill -f "python3 pyrenigma.py"
while pgrep -f pyrenigma.py >/dev/null; do sleep 0.1; done
nohup python3 pyrenigma.py > pyrenigma.log 2>&1 &
