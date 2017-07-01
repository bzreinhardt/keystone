from os import path, mkdir, remove
from os import environ
from google.cloud import storage
import audio_tools
from keyword_search import index_audio_url, audio_search
from keystone_asr import upload_folder, transcribe_in_parallel
from pprint import pprint
import json
from utility import send_simple_message, remove_bad_chars
import argparse
import shutil
from audio_tools import cut_file
import subprocess
import urllib
from time import sleep


DEFAULT_PHRASES = {
    "action item":{'type':'after'},
"that's fascinating":{'type':'before'},
"take a note":{'type':'after'},
"remember that":{'type':'before'},
}

DEFAULT_PHRASE_LENGTH_SEC = 15
FAIL_SLEEP_SEC = 2
MAX_WAIT_TIME_SEC = 1.5*60*60


def extract_audio(file):
    file = path.abspath(file)
    dir_path, filename = path.split(file)
    filename, ext = path.splitext(filename)
    if ext == '.wav':
        return file, False
    else:
        outfile = "%s/%s.wav" % (dir_path, filename)
        command = "ffmpeg -i %s -ab 160k -ac 2 -ar 44100 -vn -y %s" % (file, outfile)
        subprocess.call(command, shell=True)
        return outfile, True


def run_audio_pipeline(recording_file, call,
                       upload_original=False,
                       do_indexing=False,
                       do_transcripts=False,
                       create_clips=False,
                       retries = 0,
                       phrases={},
                       min_confidence=0.5):

    print("Extracting Audio")
    recording_path, converted = extract_audio(recording_file)

    key = call.twilio_recording_sid
    base = path.basename(recording_path)

    client = storage.Client()
    bucket = client.get_bucket('illiad-audio')
    # Keep track of whether the recording is something we downloaded
    # just for this function or whether it was already there
    temp_file = False

    if upload_original or call.recording_url is None:
        print("Uploading original file to cloud")
        blob = bucket.blob(base)
        with open(recording_path, 'rb') as f:
            blob.upload_from_file(f)
        # TODO: need to figure out secure way of actually doing this
        blob.make_public()
        url = blob.public_url
        call.recording_url = url
        call.save()
    else:
        print("skipping upload")

    if do_indexing or call.audio_index_id is None:
        tries = 0
        print("Indexing call %s" % call.twilio_recording_sid)
        deepgram_id = index_audio_url(call.recording_url)
        call.audio_index_id = deepgram_id
        call.save()
        wait_time = 0

        while wait_time < MAX_WAIT_TIME_SEC and tries <= retries:
            test = audio_search(call.audio_index_id, 'test')
            if test['error'] is None:
                break
            else:
                sleep(FAIL_SLEEP_SEC)
                wait_time = wait_time + FAIL_SLEEP_SEC
                if wait_time >= MAX_WAIT_TIME_SEC:
                    tries = tries + 1
                    deepgram_id = index_audio_url(call.recording_url)
                    call.audio_index_id = deepgram_id
                    call.save()
                    wait_time = 0
        if wait_time >= MAX_WAIT_TIME_SEC:
            print("Indexing failed for %s" % key)
            email_text = "Failed to index audio for %s" % key
            send_simple_message(subject='audio pipeline failure!',
                                text=email_text)
            return(False, key)
    else:
        print("skipping indexing")


    if call.phrase_results:
        results = json.loads(call.phrase_results)
        for phrase in results:
            if 'is_phrase' not in results[phrase]:
                results[phrase]['is_phrase'] = [False]*len(results[phrase]['startTime'])
            if 'whos' not in results[phrase]:
                results[phrase]['whos'] = ['']*len(results[phrase]['startTime'])
            if 'whats' not in results[phrase]:
                results[phrase]['whats'] = ['']*len(results[phrase]['startTime'])
            if 'wheres' not in results[phrase]:
                results[phrase]['wheres'] = ['']*len(results[phrase]['startTime'])
            if 'whens' not in results[phrase]:
                results[phrase]['whens'] = ['']*len(results[phrase]['startTime'])
            if 'whys' not in results[phrase]:
                results[phrase]['whys'] = ['']*len(results[phrase]['startTime'])
            for i, time in enumerate(results[phrase]['startTime']):
                if any([len(x) > 0 for x in [results[phrase]['whos'][i],
                                             results[phrase]['whats'][i],
                                             results[phrase]['wheres'][i],
                                             results[phrase]['whens'][i],
                                             results[phrase]['whys'][i]]]):
                    results[phrase]['is_phrase'][i] = True
            call.save()
    else:
        print("no phrase resuls")

    if len(phrases) > 0:

        call.phrases = json.dumps(phrases)
        index_ready = False
        while not index_ready:
            test = audio_search(call.audio_index_id, 'test')
            if test['error'] is None:
                index_ready = True
            sleep(2)
        phrase_times = {}

        print("searching for phrases:")
        print("phrases")
        for phrase in phrases:
            if len(phrase) == 0:
                continue
            results = audio_search(call.audio_index_id, phrase, min_confidence=min_confidence)
            if len(results) > 0:
                phrase_times[phrase] = results
            # Create clips of just the relevant audio
            if create_clips:

                if not path.isfile(recording_path):
                    temp_file = True
                    fullpath, filename = path.split(call.recording_url)
                    recording_path = "/tmp/%s"%filename
                    urllib.urlretrieve(call.recording_url, recording_path)
                directory, file = path.split(recording_path)
                name = file.split(".")[0]
                charless_phrase = remove_bad_chars(phrase)
                clip_dir = "%s/%s_%s_clips" % (directory, name, charless_phrase)
                if not path.isdir(clip_dir):
                    mkdir(clip_dir)

                    print('creating clips')

                for i, time in enumerate(results['startTime']):

                    if phrases[phrase]['type']=='before':
                        start_time = time - DEFAULT_PHRASE_LENGTH_SEC
                        stop_time = time
                    else:
                        start_time = time
                        stop_time = time + DEFAULT_PHRASE_LENGTH_SEC
                    clip_file = "%s/%s_%d.wav"%(clip_dir, charless_phrase, i)
                    print("slicing file")
                    cut_file(recording_path, start_time=start_time,
                                             stop_time=stop_time,
                                             out_file=clip_file)
                    print("sliced file")

                blob_names, urls = upload_folder(path.dirname(clip_dir), folder=path.basename(clip_dir), make_public=True)
                phrase_times[phrase]['slices'] = urls
                shutil.rmtree(clip_dir)

        call.phrase_results = json.dumps(phrase_times)
        call.save()



    if do_transcripts:
        if not path.isfile(recording_path):
            temp_file = True
            fullpath, filename = path.split(call.recording_url)
            recording_path = "/tmp/%s" % filename
            urllib.urlretrieve(call.recording_url, recording_path)
        # TODO: delete original from local filesystem
        print("Slicing audio")

        slice_dir = audio_tools.slice_wav_file(recording_path)
        print("uploading sliced folder")
        blob_names, urls = upload_folder(path.dirname(slice_dir), folder=path.basename(slice_dir))
        print("done uploading slices, finding transcript")
        words = transcribe_in_parallel(blob_names, name=key)
        print('------ transcription ------')
        pprint(words)
        # TODO: delete slices from server
        print("uploading transcript to gcloud")
        transcript_blob = bucket.blob("{}_transcript.json".format(key))
        transcript_blob.upload_from_string(json.dumps(words))
        print("done uploading transcript")
        call.transcript = json.dumps(words)
        call.save()

    if temp_file:
        remove(recording_path)

    print("FINISHED CALL %s" % key)
    display_url = "%s/alpha/backend_viewer/%s/"%("www.evoke.ai", call.twilio_recording_sid)
    email_text = "Finished processing audio for %s. Results are available at %s" % (call.caller_name, display_url)
    send_simple_message(subject='audio pipeline complete!', text= email_text )

    return (True, key)


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--twilio_id')
    parser.add_argument('--file', default='')
    parser.add_argument('--do_indexing', action='store_true', default=False)
    parser.add_argument('--do_transcripts', action='store_true', default=False)
    parser.add_argument('--create_clips', action='store_true', default=False)
    parser.add_argument('--upload_original', action='store_true', default=False)



    args = parser.parse_args()
    environ.setdefault("DJANGO_SETTINGS_MODULE", "webapp.settings")
    import django
    django.setup()
    from django.utils import timezone
    from twilio_caller.models import TwilioCall


    call = TwilioCall.objects.get(twilio_recording_sid=args.twilio_id)
    if call.participants is not None:
        participants = call.participants.split(',')
    if len(participants) > 0 and call.caller_name is None:
        call.caller_name = participants[0]
    elif call.caller_name is None:
        call.caller_name = 'unknown'
    if len(participants) > 1 and call.recipient_name is None:
        call.recipient_name = participants[1]
    elif call.recipient_name is None:
        call.recipient_name = 'unknown'
    if call.call_begin is None:
        call.call_begin = timezone.now()
    run_audio_pipeline(args.file, call, upload_original=args.upload_original,
                       do_indexing=args.do_indexing,
                       do_transcripts=args.do_transcripts,
                       create_clips=args.create_clips,
                       phrases=DEFAULT_PHRASES,
                       min_confidence=0.4)

