FROM heroku/miniconda

ADD . /keystone
WORKDIR /keystone

RUN echo heh
RUN conda env create environment.yml

WORKDIR /keystone/webapp

CMD /bin/bash -c "source activate keystone && exec python manage.py runserver"

