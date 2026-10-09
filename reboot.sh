#!/bin/bash
pkill -f "python3 pyrenigma.py"
git sync
nohup python3 pyrenigma.py > pyrenigma.log 2>&1 &