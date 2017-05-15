#!/usr/bin/python
from flask import Flask, url_for, json,  request, jsonify, render_template
import os
import boto3
import random
import string
from flask_sqlalchemy import SQLAlchemy
from argparse import ArgumentParser
import keyword_search
import keystone
import pdb
from flask_script import Manager


# These should be in a json config
BUCKET_NAME='akiajqulpiyv2ovwdt4a-dump'
SETTINGS = 'server_settings.json'

app = Flask(__name__, static_url_path='')
manager = Manager(app)
if os.environ.get('DATABASE_URL'):
  app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
else:
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)
mem_db = {"comments":dict(), "audio":dict()}

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEEPGRAM_AUDIO_ID'] = "1494481681-043d1a1b-f8c4-41ba-b82a-7dc7c4aa8368-4391418214"
print(app.instance_path)

## TODO figure out if you can make a transcript a seperate object


class Audio(db.Model):
    key = db.Column(db.String(120), primary_key=True)
    aws_url = db.Column(db.String(120))
    deepgram_id = db.Column(db.String(120))
    transcript_str = db.Column(db.String(800))
    auto_transcript_str = db.Column(db.String(800))
    transcript = dict()
    auto_transcript = dict()

    def __init__(self, key, aws_url='', deepgram_id='', transcript='', auto_transcript=''):
        self.key = key
        self.aws_url = aws_url
        self.deepgram_id = deepgram_id
        self.transcript = transcript
        self.transcript_str = json.dumps(self.transcript)
        self.auto_transcript = auto_transcript
        self.auto_transcript_str = json.dumps(self.auto_transcript)

    def __repr__(self):
        return '<Key: %s, aws_url:%s>' % (self.key, self.aws_url)

    def to_dict(self):
        return {"aws_url":self.aws_url, "deepgram_id":self.deepgram_id, "transcript":self.transcript}

    def from_dict(self, d):
        self.aws_url = d['aws_url']
        self.deepgram_id = d['deepgram_id']
        self.transcript = d['transcript']
        self.transcript_str = json.dumps(d['transcript'])


class Comment(db.Model):
    key = db.Column(db.String(120), primary_key=True)
    words = db.Column(db.String(800))
    text = db.Column(db.String(120))
    audio_id = db.Column(db.String(80))

    def __init__(self, key, words='', text='', audio_id=''):
        self.key = key
        self.words = words
        self.text = text
        self.audio_id = audio_id

    def __repr__(self):
        return '<Words: %s, comment:%s>' % (self.words, self.text)

    def to_dict(self):
        return {"words":self.words, "text":self.text, "audio_id":self.audio_id}

    def from_dict(self, d):
        self.words = d['words']
        self.text = d['text']
        self.audio_id = d['audio_id']


def load_settings(settings_file):
    with open(settings_file) as f:
        config = json.loads(f.read())
    for setting in config:
        if app.debug:
            print("Loading setting: ")
            print(setting)
            print("with value: ")
            print(config[setting])
        app.config[setting] = config[setting]
    return 0


def init_db():
    """For use on command line for setting up
    the database.
    """

    db.drop_all()
    db.create_all()

    test_comment = Comment('foo', words='test_words', text='test_text')
    db.session.add(test_comment)
    db.session.commit()
    db.session.delete(test_comment)
    db.session.commit()


def save_to_s3(key, data):
  s3 = boto3.resource('s3')
  s3.Bucket(BUCKET_NAME).put_object(Key=key, Body=data)


def db_add(comment):
    db.session.add(comment)
    if app.config['use_json_db']:
        mem_db['comments'][comment.key]=comment.to_dict()


def db_commit():
    #db.session.commit()
    if app.config['use_json_db']:
        with open(app.config['json_db'], 'w') as f:
            f.write(json.dumps(mem_db))


@app.route('/_comments')
def print_comment():
    """Add two numbers server side, ridiculous but well..."""
    comment_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    #pdb.set_trace()
    text = request.args.get('text')
    words = request.args.getlist('words[]')
    print('got comment with text %s and words'%text)
    print(words)
    response = dict()
    response['id'] = comment_id
    print(response)
    comment = Comment(comment_id, words=json.dumps(words), text=text, audio_id=request.args.get('audio_key'))
    db_add(comment)
    db_commit()
    print("saved to DB")
    return jsonify(result=response)


@app.route('/_audio')
def load_audio():
    return 0

@app.route('/_audio_search')
def audio_search():
    #This assumes the thing has already been indexed
    query = request.args.get('query')
    print("got query %s" % query)
    response = keyword_search.search_results(query, app.config['DEEPGRAM_AUDIO_ID'])
    return response




@app.route('/upload', methods=['GET', 'POST'])
def upload_image():
  
  rand = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
  if not request.form.has_key('artistName'):
    request.form['artistName'] = 'noname'
  key = request.form['artistName'] + rand
  art = Art(key, bucket=BUCKET_NAME, json_dict=request.form)
  db.session.add(art)
  db.session.commit()
  data = request.files['image'].stream.read()
  print("DATA SIZE: %s" % len(data))
  save_to_s3(key, data)
  print("SAVED TO KEY: %s"%key)
  return 'success'

@app.route('/lookup', methods=['GET', 'POST'])
def lookup_gps():
  coords = [(request.json['location']['lat'], request.json['location']['long'])]
  if len(app.DB) == 0:
    app.DB = load_db(DB_PATH)
  index = find_closest_art(app.DB, coords)

  return json.dumps({'name':app.DB[index]['name'], 'instagram':app.DB[index]['instagram']})


def startup():
    # Check if already has a deepgram ID from the database
    # Check if config wants you to load it to deepgram
    # if so load file to deepgram
    if app.config['do_audio_indexing'] and 'deepgram_id' not in mem_db['audio'][app.config['audio_key']]:
        # or len(mem_db['audio'][app.config['audio_key']]['deepgram_id']) is 0:
        # pdb.set_trace()
        deepgram_id = keyword_search.index_audio_url(mem_db['audio'][app.config['audio_key']]['aws_url'])
        mem_db['audio'][app.config['audio_key']]['deepgram_id'] = deepgram_id
        db_commit()
    # Check if alread   y has an automatic transcript
    # Check if config wants you to create an automatic transcript
    # if so get an automatic transcript from place of your choice
    if app.config['do_auto_transcript'] and 'auto_transcript' not in mem_db['audio'][app.config['audio_key']]:
        #                or len(mem_db['audio'][app.config['audio_key']]['auto_transcript']) is 0:
        foo = 'bar'
    return


@app.route('/')
def index():
    '''
    if app.debug:
        speaker_data = []
        for i, appendix in enumerate(['A', 'B', 'C', 'D']):
            #audio_name = "ES2016a.Headset-%d.wav" % i
            #audio_file = '%s/%s/audio/%s' % (DATA_DIR, dataset, audio_name)
            xml_path = "test_data/ES2016a.%s.words.xml" % (appendix)
            speaker_data.append(keystone.load_words(xml_path))

        #all_audio = {'master': '%s.Mix-Headset.wav' % (dataset)}
        words = keystone.aggregate_words(speaker_data)
        lines = keystone.generate_speaker_lines(words)
    '''
    lines = keystone.generate_speaker_lines(mem_db['audio'][app.config['audio_key']]['transcript'])
    return render_template('audio_page.html', lines=lines, audio_key=app.config['audio_key'])






if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--init_db', default=False)
    parser.add_argument('-a', '--audio_file', type=str, default='')
    parser.add_argument('-k', '--audio_key', type=str, default='')
    parser.add_argument('-i','--index', action='store_true')
    parser.add_argument('-t', '--trans', action='store_true')
    args = parser.parse_args()

    load_settings(SETTINGS)

    if args.init_db:
        app.config['init_db'] = True

    if app.config['init_db']:
        init_db()
    if app.config['use_json_db']:
        if os.path.isfile(app.config['json_db']):
            with open(app.config['json_db']) as f:
                mem_db = json.loads(f.read())

    if len(args.audio_file) > 0:
        #check if its already on aws
        aws_url = keyword_search.upload_to_aws(args.audio_file)
        app.config['audio_key'] = aws_url
        if aws_url not in mem_db['audio']:
            mem_db['audio'][aws_url] = {'aws_url': aws_url}
            db_commit()

    if len(args.audio_key) > 0:
        app.config['audio_key'] = args.audio_key

    if args.index:
        app.config['do_audio_indexing'] = True

    if args.trans:
        app.config['do_auto_transcript'] = True

    app.debug = app.config['debug']
    startup()
    app.run()

