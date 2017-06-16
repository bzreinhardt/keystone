#!/usr/bin/env bash

set -x

cd /home/ubuntu/keystone
git checkout master
git pull origin master

source activate keystone
uwsgi --socket /tmp/evoke.sock --module webapp.wsgi --chmod-socket=666 &> ~/logs/uwsgi.log &
