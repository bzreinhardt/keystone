#!/usr/bin/env bash

echo '= pulling latest code'
cd /home/ubuntu/keystone
git reset --hard HEAD
git checkout master
git pull origin master

echo '= setting DEBUG = True'
sed -i 's/DEBUG = True/DEBUG = False/g' webapp/webapp/settings.py

cd /home/ubuntu/keystone/webapp
export PATH=/home/ubuntu/miniconda3/bin:$PATH
echo '= source ~/keystone_env.sh'
source ~/keystone_env.sh
echo '= source activate keystone'
source activate keystone
echo '= killing any uwsgi processes'
killall uwsgi || true
echo '= running uwsgi for webapp'
uwsgi --socket /tmp/evoke.sock --module webapp.wsgi --chmod-socket=666 &> ~/logs/uwsgi.log &
