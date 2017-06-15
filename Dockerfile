FROM heroku/miniconda

ADD . /keystone
WORKDIR /keystone

RUN apt-get update
RUN apt-get install -y gcc libssl-dev libffi-dev libsndfile-dev ffmpeg
RUN conda env create environment.yml

WORKDIR /keystone/webapp

CMD /bin/bash -c "source activate keystone && exec python manage.py runserver"

