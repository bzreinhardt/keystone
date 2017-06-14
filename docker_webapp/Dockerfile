FROM heroku/miniconda

ADD . /keystone
WORKDIR /keystone

RUN conda env create environment.yml
RUN source activate keystone2

WORKDIR /keystone/webapp

RUN python manage.py runserver