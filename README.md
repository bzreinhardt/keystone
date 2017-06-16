# Keystone

Automatic note-taking.

### Setup
Clone this repo to your local machine

```bash
git clone https://github.com/bzreinhardt/keystone
cd keystone
export KEYSTONE=${pwd}
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

### Run our web server

```
cd keystone/webapp
python manage.py runserver
```

You should see a few messages saying that the server found an ngrok tunnel, something like `d7b5194.ngrok.io`.  Go there in a web browser and you should see our web app.

### Amicorpus data

Download amicorpus data
```bash
run set_up_data.sh
```

Example processing and html creation
```bash
python keystone.py
```

If you are dealing with .mp3 files you will need to install <b>libav or ffmpeg</b> 
Mac
```bash
### libav
brew install libav --with-libvorbis --with-sdl --with-theora

####    OR    #####

# ffmpeg
brew install ffmpeg --with-libvorbis --with-ffplay --with-theora
```

### Adding a File

To upload an audio file to aws and associate it with a transcript, use

```bash
python add_audio_to_db.py --audio_file <path to audio file> --xml_transcripts_folder <path to a folder with an amicorpus style xml transcript for each speaker> -n <name that you want to be associated with this file> 
```
To try it out with the defaults from the ```webapp/test_data``` folder, use the ```-d``` flag.

Right now there is no internet-based web app so I am using an extremely hacky json file to keep track of data. So to save things, you need to git commit the file.

### Webapp

To run the webapp

```bash
cd $KEYSTONE/webapp
python manage.py runserver
```

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
