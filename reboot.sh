#!/bin/bash
export HOME="/home/firebot"
export USER="firebot"
export LOGNAME="firebot"
export PATH="/usr/local/bin:/usr/bin:/bin"
export LANG="C.UTF-8"
export LC_ALL="C.UTF-8"
export PYTHONUNBUFFERED="1"
PYTHON="/usr/bin/python3"
SCRIPT="/home/firebot/git/Emberbot137/pyrenigma.py"
LOG="/home/firebot/git/Emberbot137/pyrenigma.log"
if /usr/bin/pgrep -f "[p]ython3 /home/firebot/git/Emberbot137/pyrenigma.py" >/dev/null 2>&1; then
    /usr/bin/pkill -TERM -f "[p]ython3 /home/firebot/git/Emberbot137/pyrenigma.py"
    while /usr/bin/pgrep -f "[p]ython3 /home/firebot/git/Emberbot137/pyrenigma.py" >/dev/null 2>&1; do
        /usr/bin/sleep 0.1
    done
fi
cd /home/firebot/git/Emberbot137 || exit 1
/usr/bin/nohup "$PYTHON" "$SCRIPT" >> "$LOG" 2>&1 </dev/null &
