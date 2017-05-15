# Keystone

Automatic note-taking.

### Setup
Clone this repo to your local machine

```bash
git clone https://github.com/bzreinhardt/keystone
cd keystone
export KEYSTONE=${pwd}
```

Create a Conda environment (You will need to [Install Conda](https://conda.io/docs/install/quick.html) first)

```bash
cd $KEYSTONE
conda env create environment.yml
source activate keystone
```

Download amicorpus data
```bash
run set_up_data.sh
```

Example processing and html creation
```bash
python keystone.py
```

If  you are dealing with .mp3 files you will need to install <b>libav or ffmpeg</b> 
Mac
```bash
# libav
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
python server.py
```
This will start a webapp that lets you start to play with transcripts and audio. Right now it will let you delete irrelevant text, add comments, and collapse text into topics. It will also let you do audio indexing on database entries.

Going to 127.0.0.1 will show you a list of the audio_keys in the database
127.0.0.1/audio/<audio_key> will take you to a page for that specific key

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
