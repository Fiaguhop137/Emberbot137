#!/bin/bash
set -e
export PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/sbin:/usr/sbin:/sbin
export HOME=/home/firebot
export USER=firebot
export LOGNAME=firebot
export XDG_RUNTIME_DIR=/run/user/1000
cd /home/firebot/git/Emberbot137
/usr/bin/pkill -f "discord.py" || :
/usr/bin/sleep 1
/usr/bin/nohup /usr/bin/python3 /home/firebot/git/Emberbot137/encrypt.py > /dev/null 2>&1 &
/usr/bin/nohup /usr/bin/python3 /home/firebot/git/Emberbot137/discord_tunnel.py > /home/firebot/git/Emberbot137/discord.log 2>&1 &
/usr/bin/sleep 1
/home/firebot/Downloads/shell/git-sync.sh || :