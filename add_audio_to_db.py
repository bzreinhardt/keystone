import keystone
import json
import argparse
import os
import random
import keyword_search
import keystone_asr
import string
import pdb

DEFAULT_XML_TRANSCRIPTS_FOLDER = "%s/webapp/test_data"%os.environ['KEYSTONE']
DEFAULT_DB_FILE= "%s/webapp/db.json"%os.environ['KEYSTONE']
DEFAULT_AUDIO_FILE="%s/webapp/test_data/"%os.environ['KEYSTONE']

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio_file')
    parser.add_argument('--xml_transcripts_folder')
    parser.add_argument('--ibm_transcript_file')
    parser.add_argument('-n', '--name', default='')
    parser.add_argument('-d','--defaults', action='store_true')
    parser.add_argument('-t', '--transcript', action='store_true')
    args = parser.parse_args()

    audio_key = args.name
    audio_file = args.audio_file
    xml_transcripts_folder = args.xml_transcripts_folder

    if args.defaults:
        audio_file = DEFAULT_AUDIO_FILE
        xml_transcripts_folder = DEFAULT_XML_TRANSCRIPTS_FOLDER

    if os.path.isfile(DEFAULT_DB_FILE):
        #pdb.set_trace()
        with open(DEFAULT_DB_FILE, 'r') as f:
            mem_db = json.loads(f.read())
    else:
        mem_db = {"audio":dict(), "comments":dict()}

    speaker_data = []
    for file in os.listdir(xml_transcripts_folder):
        if file.split('.')[-1] == 'xml':
            full_path = os.path.join(args.xml_transcripts_folder, file)
            speaker_data.append(keystone.load_words(full_path))

    words = keystone.aggregate_words(speaker_data)

    if len(words) > 0:
        if audio_key in mem_db['audio']:
            mem_db['audio'][audio_key]['transcript'] = words
        else:
            mem_db['audio'][audio_key] = {'transcript': words}

    if audio_file:
        aws_url = keyword_search.upload_to_aws(audio_file)
        if audio_key == '':
            audio_key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        if audio_key not in mem_db['audio']:
            mem_db['audio'][audio_key] = {'aws_url': aws_url}
        else:
            mem_db['audio'][audio_key]['aws_url'] = aws_url

    # create a transcript with the file
    ibm_transcript = None
    if args.transcript:
        # if it's not a local file, you have to download it from aws - super hacky
        ibm_transcript = keystone_asr.run_watson(audio_file, transcript_file="%s/ibm_transcript.json"%os.path.split(audio_file)[0])
        mem_db['audio'][audio_key]['ibm__transcript'] = ibm_transcript
    elif args.ibm_transcript_file:
        with open(args.ibm_transcript_file, 'r') as f:
            ibm_transcript = json.loads(f.read())

    if ibm_transcript:
        words = keystone_asr.words_from_json(ibm_transcript, name=audio_key)
        mem_db['audio'][audio_key]['ibm_transcript'] = words

    with open(DEFAULT_DB_FILE, 'w') as f:
        f.write(json.dumps(mem_db))