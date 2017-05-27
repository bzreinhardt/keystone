#!/usr/bin/env python3

from pprint import pprint
import imp
import argparse

import os, sys, inspect
import speech_recognition as sr

# obtain path to "english.wav" in the same folder as this script
from os import path
import json
import time
import pdb
#from credentials import credentials

FILE_NAME = "ES2016a.Mix-Headset"
DIR_NAME = "/Users/Zaaron/Data/audio"
AUDIO_FILE = path.join(DIR_NAME, "%s.wav" % FILE_NAME)
CLOUD_AUDIO_FILE = "gs://illiad-audio/ES2016a.Mix-Headset.flac"
TRANSCRIPT_FILE = path.join(DIR_NAME, "%s_google_transcript.json" % FILE_NAME)
DURATION = 59
# AUDIO_FILE = path.join(path.dirname(path.realpath(__file__)), "french.aiff")
# AUDIO_FILE = path.join(path.dirname(path.realpath(__file__)), "chinese.flac")


def wav_to_flac(audio_file, duration=None, stereo_to_mono=False):
    (directory, filename) = os.path.split(audio_file)
    name = ".".join(filename.split(".")[:-1])
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        # If the file is stereo this will be a list if stereo_to_mono is false
        audio = r.record(source, duration=duration, stereo_to_mono=stereo_to_mono)
    out_name_base = "%s/%s"  % (directory, name)
    if duration:
        out_name_base = "%s_%d" % duration
    if source.audio_reader.getnchannels() > 1 and not stereo_to_mono:
        out_left = "%s_l.flac" % out_name_base
        out_right = "%s_r.flac" % out_name_base
        r.write_flac(audio[0], out_left)
        r.write_flac(audio[1], out_right)
        file = (out_left, out_right)
    else:
        out_name = "%s.flac" % out_name_base
        r.write_flac(audio, out_name)
        file = out_name
    return file

def assign_speaker_labels(words, speakers):
    # assumes words and speakers are all in temporal order
    current_time = 0.0
    current_label = 0
    current_word = 0


def words_from_json(watson_json, name=""):
    """
    Turns a watson json into a word dict
    :param watson_json: Json string in the watson format 
    :return: 
    """
    # go through and pull out words, give them ids
    words = []
    for result in watson_json['results']:
        #    pdb.set_trace()

        for i, word in enumerate(result['alternatives'][0]['timestamps']):
            word_id = "%s_word_%d" % (name, i)
            text = word[0]
            start = word[1]
            end = word[2]
            confidence = result['alternatives'][0]['word_confidence'][i][1]
            word = {'id': word_id, 'text': text, 'starttime': start, 'endtime': end, 'confidence': confidence}
            words.append(word)

        #assign speakers
    if 'speaker_labels' in watson_json:
        speaker_index = 0
        for word in words:
            # naive approach to just assign each word the speaker who is talking in the middle of the word
            mean_time = (word['starttime'] + word['endtime'])/2.0
            while not (watson_json['speaker_labels'][speaker_index]['from'] < mean_time and
                               watson_json['speaker_labels'][speaker_index]['to'] > mean_time):
                speaker_index += 1
            word['speaker'] = watson_json['speaker_labels'][speaker_index]['speaker']
            word['speaker_confidence'] = watson_json['speaker_labels'][speaker_index]['confidence']
    return words



    # go through


# TODO: find if you can run watson from a url
# TODO: this really needs to be asyncronous
def run_watson(audio_file, duration=None, transcript_file=''):
    # use the audio file as the audio source
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source, duration=duration)  # read the entire audio file
    try:
        transcript = r.recognize_ibm(audio,
                                     username=credentials['watson']['username'],
                                     password=credentials['watson']['password'],
                                     show_all=True)

    except sr.UnknownValueError:
        print("IBM Speech to Text could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from IBM Speech to Text service; {0}".format(e))
    if len(transcript_file) > 0:
        with open(transcript_file, 'w') as f:
            f.write(json.dumps(transcript, indent=4))
    return transcript


def run_google(audio_file, duration=None, transcript_file=''):
    # recognize speech using Google Speech Recognition
    r = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = r.record(source, duration=duration)
    """
    try:
        # for testing purposes, we're just using the default API key
        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY", show_all=True)`
        # instead of `r.recognize_google(audio, show_all=True)`
        print("Google Speech Recognition results:")
        pprint(r.recognize_google(audio, show_all=True))  # pretty-print the recognition result
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
    """
    # recognize speech using Google Cloud Speech
    with open(credentials["google"]["file"], 'r') as f:
        GOOGLE_CLOUD_SPEECH_CREDENTIALS = f.read()
    try:
        print("Google Cloud Speech recognition results:")
        result = r.recognize_google_cloud(audio, credentials_json=GOOGLE_CLOUD_SPEECH_CREDENTIALS,
                                        show_all=True)  # pretty-print the recognition result
        pprint(result)
        if len(transcript_file) > 0:
            with open(transcript_file, 'w') as f:
                f.write(json.dumps(result))

    except sr.UnknownValueError:
        print("Google Cloud Speech could not understand audio")
    except sr.RequestError as e:
        print("Could not request results from Google Cloud Speech service; {0}".format(e))

def transcribe_gcs(gcs_uri, name=""):
    """Asynchronously transcribes the audio file specified by the gcs_uri."""
    from google.cloud import speech
    speech_client = speech.Client()

    audio_sample = speech_client.sample(
        content=None,
        source_uri=gcs_uri,
        encoding='FLAC',
        sample_rate_hertz=8000)

    operation = audio_sample.long_running_recognize('en-US')

    retry_count = 100
    while not operation.complete:
        retry_count -= 1
        time.sleep(2)
        operation.poll()

    if not operation.complete:
        print('Operation not complete and retry limit reached.')
        return

    alternatives = operation.results
    words = []
    for i, alternative in enumerate(alternatives):
        words.append({"id":"%s_%d"%(name, i), "text":alternative.transcript, "confidence":alternative.confidence})
    return words

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="test")
    parser.add_argument("--transcribe", action="store_true")
    parser.add_argument("--convert", action="store_true")
    parser.add_argument("--audio_file")

    args = parser.parse_args()
    if args.transcribe:
        transcript_file = "%s_google_transcript.json" % args.name
        audio_file = args.audio_file
        name = args.name
        transcript = transcribe_gcs(audio_file, name=name)
        with open(transcript_file, 'w') as f:
            f.write(json.dumps(transcript))
    if args.convert:
        wav_to_flac(args.audio_file)



"""
# recognize speech using Sphinx
try:
    print("Sphinx thinks you said " + r.recognize_sphinx(audio))
except sr.UnknownValueError:
    print("Sphinx could not understand audio")
except sr.RequestError as e:
    print("Sphinx error; {0}".format(e))
    
    
# recognize speech using Wit.ai
WIT_AI_KEY = "INSERT WIT.AI API KEY HERE"  # Wit.ai keys are 32-character uppercase alphanumeric strings
try:
    print("Wit.ai recognition results:")
    pprint(r.recognize_wit(audio, key=WIT_AI_KEY, show_all=True))  # pretty-print the recognition result
except sr.UnknownValueError:
    print("Wit.ai could not understand audio")
except sr.RequestError as e:
    print("Could not request results from Wit.ai service; {0}".format(e))

# recognize speech using Microsoft Bing Voice Recognition
BING_KEY = "INSERT BING API KEY HERE"  # Microsoft Bing Voice Recognition API keys 32-character lowercase hexadecimal strings
try:
    print("Bing recognition results:")
    pprint(r.recognize_bing(audio, key=BING_KEY, show_all=True))
except sr.UnknownValueError:
    print("Microsoft Bing Voice Recognition could not understand audio")
except sr.RequestError as e:
    print("Could not request results from Microsoft Bing Voice Recognition service; {0}".format(e))

# recognize speech using Houndify
HOUNDIFY_CLIENT_ID = "INSERT HOUNDIFY CLIENT ID HERE"  # Houndify client IDs are Base64-encoded strings
HOUNDIFY_CLIENT_KEY = "INSERT HOUNDIFY CLIENT KEY HERE"  # Houndify client keys are Base64-encoded strings
try:
    print("Houndify recognition results:")
    pprint(r.recognize_houndify(audio, client_id=HOUNDIFY_CLIENT_ID, client_key=HOUNDIFY_CLIENT_KEY, show_all=True))
except sr.UnknownValueError:
    print("Houndify could not understand audio")
except sr.RequestError as e:
    print("Could not request results from Houndify service; {0}".format(e))
"""
