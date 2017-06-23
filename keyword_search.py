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
MAX_DISTANCE_BETWEEN_KEYWORDS = 2
DEFAULT_MIN_CONFIDENCE=0.4
DEFAULT_MAX_RETURNS = 10


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
    # Statuses:
    # "fetch"
    # "awaiting_gen_lattice"
    # "done"
    data = {"action": "get_object_status", "userID": DEEPGRAM_KEY, "contentID": content_id}
    status = requests.post(DEEPGRAM_URL, headers=headers, data=json.dumps(data))
    return status.text




def audio_search(content_id, query, min_confidence=DEFAULT_MIN_CONFIDENCE, max_returns=DEFAULT_MAX_RETURNS, sort_field="P"):
    """
    
    :param content_id: deepgram id string
    :param query: string to search for
    :return: dictionary of lists - {"snippet", "P", "endTime", "startTime", "N", "error")
    """
    data = {"action": "object_search", "userID": DEEPGRAM_KEY, "contentID": content_id,
            "query": query, "snippet": False, "filter": {"Nmax": max_returns, "Pmin": min_confidence}, "sort": "time"}

    status = requests.post(DEEPGRAM_URL, headers=headers, data=json.dumps(data))
    # will return error if it's not indexed yet
    out = json.loads(status.text)
    if "error" not in out:
        out["error"] = None
        # Sort by whatever field you want
        sort_array = out[sort_field]
        for field in out.keys():
            if field == "error":
                continue
            copy_sort_array = sort_array
            out[field] = [x for (y,x) in sorted(zip(copy_sort_array, out[field]), reverse=True)]
    return out

def phrase_search(content_id, phrase):
    """
    :param content_id: 
    :param phrase: 
    :return: List of start times where the key phrase was detected
    """
    """ THIS GOT WAY TOO FANCY
    words = phrase.split(" ")
    results = []
    for word in words:
        data = {"action": "object_search", "userID": DEEPGRAM_KEY, "contentID": content_id,
                "query": word, "snippet": True, "filter": {"Nmax": 10, "Pmin": 0.55}, "sort": "time"}
        status = requests.post(DEEPGRAM_URL, headers=headers, data=json.dumps(data))
        results.append(json.loads(status.text))
    # This forces the word order to remain the same for now
    all_potential_pairs = []
    for i, result in enumerate(results[0:-1]):
        potential_pairs = []
        for j, time_a in enumerate(result['startTime']):
            for k, time_b in enumerate(results[i+1]['startTime']):
                d = time_b - time_a
                if abs(d) < MAX_DISTANCE_BETWEEN_KEYWORDS:
                    potential_pairs.append([j,k])
        all_potential_pairs.append(potential_pairs)
    # Seed the potential chains with the pairs
    potential_chains = all_potential_pairs[0]
    i = 1

    while i <= len(all_potential_pairs) - 1:
        new_potential_chains = []
        for chain in potential_chains:
            for pair in all_potential_pairs[i+1]:
                if len(chain) == 0:
                    pdb.set_trace()
                index_a = chain[-1]
                index_b = pair[0]
                try:
                    d = abs(results[i]['startTime'][index_a] - results[i+1]['startTime'][index_b])
                except:
                    pdb.set_trace()
                if d < MAX_DISTANCE_BETWEEN_KEYWORDS:
                    new_chain = chain + pair
                    new_potential_chains.append(new_chain)
        potential_chains = new_potential_chains
        i += 1
    start_times = []
    for chain in potential_chains:
        start_times.append(results[0]['startTime'][chain[0]])
    return start_times

"""





if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--key")
    parser.add_argument("--upload", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--search")
    parser.add_argument("--full_stack", action="store_true")
    args = parser.parse_args()
    DB_FILE = "%s/experimental_webapp/db.json" % os.environ["KEYSTONE"]
    KEY = "ben_noah_5_23"
    URL = "https://storage.googleapis.com/illiad-audio/twilio_REf4c874b065c4e2491825e63d571de3dc.wav"
    KEY2 = "twilio_REf4c874b065c4e2491825e63d571de3dc"
    with open(DB_FILE, 'r') as f:
        db = json.loads(f.read())
    if not args.key:
        key = KEY
    else:
        key = args.key
    if args.upload:
        url = db['audio'][KEY]['aws_url']
        print("Indexing audio from %s" % url)
        deepgram_id = index_audio_url(url)
        db['audio'][KEY]['deepgram_id'] = deepgram_id
        with open(DB_FILE, 'w') as f:
            f.write(json.dumps(db))
        print(get_indexing_status(deepgram_id))
    if args.status:
        deepgram_id = db['audio'][KEY]['deepgram_id']
        print(get_indexing_status(deepgram_id))
    if args.search:

        deepgram_id = db['audio'][KEY]['deepgram_id']
        print("deepgram ID:")
        print(deepgram_id)
        print(audio_search(deepgram_id, args.search))
    if args.full_stack:
        pdb.set_trace()
        deepgram_id = index_audio_url(URL)
        db['audio'][KEY2] = dict()
        db['audio'][KEY2]['deepgram_id'] = deepgram_id
        with open(DB_FILE, 'w') as f:
            f.write(json.dumps(db))
        print(audio_search(deepgram_id, "test"))
        #while get_indexing_status(deepgram_id) != "done":
        #    sys.stdout.write("Waiting for index to ")



    """ # This is the id for the ES2016a.Mix-Headset.wav file
    content_id = "1494481681-043d1a1b-f8c4-41ba-b82a-7dc7c4aa8368-4391418214"
    query = args.query
    search_results = audio_search(content_id, query)
    print(search_results)
    """

