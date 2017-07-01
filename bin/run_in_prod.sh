#!/usr/bin/env bash

echo '= pulling latest code'
cd /home/ubuntu/keystone
git reset --hard HEAD
git checkout master
git pull origin master

export PYTHONPATH=$(pwd):$PYTHONPATH

echo '= setting DEBUG = True'
sed -i 's/DEBUG = True/DEBUG = False/g' webapp/webapp/settings.py

cd /home/ubuntu/keystone/webapp
export PATH=/home/ubuntu/miniconda3/bin:$PATH
echo '= source ~/keystone_env.sh'
source ~/keystone_env.sh
echo '= source activate keystone'
source activate keystone
echo '= killing any uwsgi processes'
set +e
pkill -f uwsgi || true
echo '= killing any worker processes'
pkill -f manage.py || true
set -e
echo '= running uwsgi for webapp'
uwsgi --socket /tmp/evoke.sock --module webapp.wsgi --chmod-socket=666 &> ~/logs/uwsgi.log &
echo '= starting background worker'
python manage.py worker &> ~/logs/worker.log &
