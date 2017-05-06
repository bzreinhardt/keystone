### Setup
Clone this repo to your local machine

```bash
git clone https://github.com/bzreinhardt/keystone
cd keystone
export KEYSTONE=${pwd}
```

Create a Conda environment (You will need to [Install Conda](https://conda.io/docs/install/quick.html) first)

```bash
conda create --name keystone python=3
source activate keystone
cd $KEYSTONE
pip install -r requirements.txt
```

Download amicorpus data
```bash
run set_up_data.sh
```

Example processing and html creation
```bash
python keystone.py
```

TODO:

DONE finish download script

make words into a class

aggregate things by speaker 
