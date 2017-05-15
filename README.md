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
