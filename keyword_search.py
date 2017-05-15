import requests, json

import boto
import sys
import os
import argparse
import pdb

AWS_ACCESS_KEY_ID = 'AKIAJ33XPTGEMXMCQTXA'
AWS_SECRET_ACCESS_KEY = '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'
DEEPGRAM_URL = 'https://api.deepgram.com'
DEEPGRAM_SEARCH_URL = 'https://groupsearch.api.deepgram.com'
BUCKET_NAME = 'actionitem'
headers = {'Content-Type': 'application/json'}


DEEPGRAM_KEY="1493278813-9f3f167a-a486-41b6-9f5a-ababa889ec10-6231941426800457280262168346310"
ES2016_MIXED_CONTENT_ID = "1494481681-043d1a1b-f8c4-41ba-b82a-7dc7c4aa8368-4391418214"

def percent_cb(complete, total):
    sys.stdout.write('.')
    sys.stdout.flush()


def upload_to_aws(filename, aws_path=None, overwrite=False):
    """
    
    :param filename: 
    :param aws_path: Desired path for the resource inside the aws bucket
    :return: public url of resource
    """
    filename = os.path.abspath(filename)
    conn = boto.connect_s3(AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    bucket = conn.get_bucket(BUCKET_NAME)
    k = boto.s3.key.Key(bucket)
    if aws_path is None:
        aws_path = filename.split('raw_data/')[-1]
    k.key = aws_path
    url = k.generate_url(expires_in=0, query_auth=False)
    if not k.exists():
        test_file = filename
        # TODO - print file size and give an idea of how long it should take
        print('Loading to AWS ... ')
        k.set_contents_from_filename(test_file, cb=percent_cb, num_cb=10)
    return url


def index_audio_url(url):
    """
    
    :param url: 
    :return: deepgram content id
    """
    data = {"action": "index_content", "userID": DEEPGRAM_KEY, "data_url": url}
    out = requests.post(DEEPGRAM_URL, headers=headers, data=json.dumps(data))
    return json.loads(out.text)['contentID']


def get_indexing_status(content_id):
    data = {"action": "get_object_status", "userID": DEEPGRAM_KEY, "contentID": content_id}
    status = requests.post(DEEPGRAM_URL, headers=headers, data=json.dumps(data))
    return status.text


def audio_search(content_id, query):
    data = {"action": "object_search", "userID": DEEPGRAM_KEY, "contentID": content_id,
            "query": query, "snippet": True, "filter": {"Nmax": 10, "Pmin": 0.55}, "sort": "time"}
    status = requests.post(DEEPGRAM_URL, headers=headers, data=json.dumps(data))
    return status.text

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    args = parser.parse_args()
    # This is the id for the ES2016a.Mix-Headset.wav file
    content_id = "1494481681-043d1a1b-f8c4-41ba-b82a-7dc7c4aa8368-4391418214"
    query = args.query
    search_results = audio_search(content_id, query)
    print(search_results)

