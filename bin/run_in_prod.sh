#!/usr/bin/env bash

set -x

cd /home/ubuntu/keystone
git reset --hard HEAD
git checkout master
git pull origin master

sed -i 's/DEBUG = True/DEBUG = False/g' webapp/webapp/settings.py

cd /home/ubuntu/keystone/webapp
export PATH=/home/ubuntu/miniconda3/bin:$PATH
set +x
echo '= source ~/keystone_env.sh'
source ~/keystone_env.sh
echo '= source activate keystone'
source activate keystone
echo '= killing any uwsgi processes'
killall -q uwsgi
set -x
uwsgi --socket /tmp/evoke.sock --module webapp.wsgi --chmod-socket=666 &> ~/logs/uwsgi.log &
