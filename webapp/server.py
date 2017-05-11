#!/usr/bin/python
from flask import Flask, url_for, json,  request, jsonify, render_template
import os
import boto3
import random
import string
from flask_sqlalchemy import SQLAlchemy
from argparse import ArgumentParser
import keyword_search
import pdb


# These should be in a json config
BUCKET_NAME='akiajqulpiyv2ovwdt4a-dump'

app = Flask(__name__, static_url_path='')
if os.environ.get('DATABASE_URL'):
  app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
else:
  app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['DEEPGRAM_AUDIO_ID'] = "1494481681-043d1a1b-f8c4-41ba-b82a-7dc7c4aa8368-4391418214"
print(app.instance_path)

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
    comment = Comment(comment_id, words=json.dumps(words), text=text)
    db.session.add(comment)
    db.session.commit()
    print("saved to DB")
    return jsonify(result=response)

@app.route('/_audio_search')
def audio_search():
    #This assumes the thing has already been indexed
    query = request.args.get('query')
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


@app.route('/')
def index():
    #return render_template('index.html')
    return render_template('no_audio_test.html')


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('init_db', default=False)
    args = parser.parse_args()
    if args.init_db:
        init_db()

    app.debug = True
    app.run()
