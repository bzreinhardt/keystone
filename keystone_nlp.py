import nltk.data
import json
import keystone
import argparse
import re
from itertools import groupby
from operator import itemgetter

DB = '/Users/Zaaron/Code/keystone/experimental_webapp/db.json'
KEY = 'test_audio'

def clean_up_sentence(sentence):
    #Replace "he was . like" with "he said"


def pull_out_relevent(sentence_list):
    """
    Right n
    :param transcript: 
    :return: 
    """

    important_sentences = []
    action_sentences = []
    for i, sentence in enumerate(sentence_list):
        # Rule: if there is a question, pull out the sentence after it
        if sentence[-1] is "?":
            important_sentences.append(i+1)
        if re.search(r"[Ii][ ']((will)|(ll))", sentence):
            action_sentences.append(i)
        if re.search(r"going to", sentence):
            action_sentences.append(i)
        if re.search(r"action item", sentence):
            action_sentences.append(i)
        if re.search(r"[Nn]ext time", sentence):
            action_sentences.append(i)
            # Rule: if someone says they will do something it's an action
        if re.search(r"[Ii][ ']((have)|(ve))", sentence):
            important_sentences.append(i)
        if re.search(r"[Pp]lan", sentence):
            important_sentences.append(i)
        if re.search(r"[Ii]nteresting", sentence):
            important_sentences.append(i)

    return important_sentences, action_sentences

def process_sentences(sentence_indices, sentence_list=None):
    indices = sorted(sentence_indices, key=int)
    indices = list(set(indices))
    return indices

def create_groups(int_list):
    group_list = []
    for k, g in groupby(enumerate(int_list), lambda ix: ix[0] - ix[1]):
        group_list.append(list(map(itemgetter(1), g)))
    return group_list


def create_notes(important_indices, action_indices, sentence_list):
    import pdb
    #pdb.set_trace()
    action_groups = create_groups(action_indices)
    important_groups = create_groups(important_indices)
    # merge sentences that are consecutive
    action_sentences = []
    important_sentences = []
    for group in important_groups:
        important_sentences.append((" ").join([sentence_list[i] for i in group]))
    for group in action_groups:
        action_sentences.append((" ").join([sentence_list[i] for i in group]))
    return important_sentences, action_sentences



if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    args = parser.parse_args()
    tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')
    with open(args.file, 'r') as f:
        transcript = json.loads(f.read())
    data = keystone.word_list_to_string(transcript)
    sentences = tokenizer.tokenize(data)
    important_indices, action_indices = pull_out_relevent(sentences)
    important_indices = process_sentences(important_indices)
    action_indices = process_sentences(action_indices)
    important_sentences, action_sentences = create_notes(important_indices, action_indices, sentences)
    
    divider = '\n-----\n'
    print ("IMPORTANT SENTENCES:")
    print (divider.join(important_sentences))
    print("\n ACTION SENTENCES:")
    print (divider.join(action_sentences))


