# Keystone

Automatic note-taking.

### Setup
Clone this repo to your local machine

```bash
git clone https://github.com/bzreinhardt/keystone
cd keystone
export KEYSTONE=${pwd}
```
You will need several environment variables. It is probably a good idea to put them in your ~/.bashrc or a 
setup.sh file that you source. Ask Ben or Noah for the twilio, google and oath credentials.

```bash
export GOOGlE_APPLICATION_CREDENTIALS=<path-to-config-json>
export TWILIO_ACCOUNT_SID=<string with twilio sid>
export TWILIO_AUTH_TOKEN=<string with twilio auth>
export OAUTH2_CLIENT_ID=<oath2 client id>
export OAUTH2_CLIENT_SECRET=<oath2 client secret>
export KEYSTONE=<path to project dir>
export PYTHONPATH=$KEYSTONE:$PYTHONPATH
export PYTHONPATH=$KEYSTONE/webapp:$PYTHONPATH
export DATA_DIR=/tmp/
```

If you plan to use Google for speech recognition, obtain the credentials json file with these instructions [instructions](https://cloud.google.com/speech/docs/common/auth) and 
```bash
$ export GOOGLE_APPLICATION_CREDENTIALS=<path_to_service_account_file>
```

Create a Conda environment (You will need to [Install Conda](https://conda.io/docs/install/quick.html) first)

```bash
cd $KEYSTONE
conda env create environment.yml
source activate keystone
```

### Install ngrok

Ngrok is a tunnel used to expose your development web server to the public web.  This is necessary for Twilio's webhooks API.

Download [ngrok](http://ngrok.com).  Unzip the package, which just contains a binary, and move it to some directory on your `$PATH`--I use `~/bin/`.  Run `ngrok http 8000` to set up a proxy to your machine at port 8000, which is where the Django development server will listen.


### Webapp

To run the webapp locally first create a ngrok instance
```bash
ngrok http 8000
```
And in a new shell

```bash
cd $KEYSTONE/webapp
python manage.py runserver
```

You should see a few messages saying that the server found an ngrok tunnel, something like `d7b5194.ngrok.io`.  Go there in a web browser and you should see our web app.

To understand how our webapp works in production, consult the [Django and nginx uwsgi tutorial][uwsgi].

To deploy the webapp, run:

    ./deploy_webapp.sh

Make sure you have the private key for AWS, `adam.pem`, in your .ssh
directory.

[uwsgi]: http://uwsgi-docs.readthedocs.io/en/latest/tutorials/Django_and_nginx.html

### Transcripts

Proposed official transcript format:
List of words which are dictionaries with the following fields:
'starttime'
'endtime'
'text'
'speaker'
'confidence'

TODO:

DONE finish download script

make words into a class

aggregate things by speaker 
