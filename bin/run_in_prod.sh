#!/usr/bin/env bash

set -x

cd /home/ubuntu/keystone
git reset --hard HEAD
git checkout master
git pull origin master

sed -i 's/DEBUG = True/DEBUG = False/g' webapp/webapp/settings.py

cd /home/ubuntu/keystone/webapp
source activate keystone
killall uwsgi
uwsgi --socket /tmp/evoke.sock --module webapp.wsgi --chmod-socket=666 &> ~/logs/uwsgi.log &
