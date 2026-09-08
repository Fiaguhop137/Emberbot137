#!/bin/bash
set -e

export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin
export HOME=/home/firebot
export USER=firebot
export LOGNAME=firebot
export XDG_RUNTIME_DIR=/run/user/1000

cd /home/firebot/git/Emberbot137
sleep 1

/usr/bin/pkill -f "emberbot137.py" || :
/usr/bin/pkill -x "xz" || :

/home/firebot/Downloads/shell/git-sync.sh || :

/usr/bin/nohup /usr/bin/python3 /home/firebot/git/Emberbot137/emberbot137.py \
    > /home/firebot/git/Emberbot137/emberbot137.log 2>&1 &
