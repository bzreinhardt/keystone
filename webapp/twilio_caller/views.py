from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from twilio.rest import Client as Twilio
from django import forms
from os import environ
from os import path
import sys
import json

import requests

from google.cloud import storage

from twilio_caller.models import TwilioCall

# TODO: https://stackoverflow.com/a/3856947/554487
sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
import audio_tools
from keystone_asr import wav_to_flac, transcribe_gcs, upload_folder, transcribe_slices, transcribe_in_parallel
from pprint import pprint
from keyword_search import index_audio_url, audio_search
from keystone import generate_speaker_lines, sort_words, confidence_to_hex

twilio = Twilio(environ.get('TWILIO_ACCOUNT_SID'),
                environ.get('TWILIO_AUTH_TOKEN'))

UPLOAD_ORIGINAL = False
DO_TRANSCRIPTS = True
DO_INDEXING = False

HACK_DB = "%s/experimental_webapp/db.json" % environ.get('KEYSTONE')
if HACK_DB:
    with open(HACK_DB, 'r') as f:
        mem_db = json.loads(f.read())
        print('available recordings are: ')
        print(mem_db['audio'].keys())

class ReusableForm(forms.Form):
    name = forms.CharField(label='Name:', max_length=100)

def index(request):
    return render(request, 'twilio_caller/callform.html')

@require_http_methods(["POST"])
def call(request):
    call = TwilioCall.objects.create(
        caller_name=request.POST['caller-name'],
        caller_email=request.POST['caller-email'],
        caller_number=request.POST['caller-number'],
        recipient_name=request.POST['recipient-name'],
        recipient_email=request.POST['recipient-email'],
        recipient_number=request.POST['recipient-number'])
    call.save()

    twilio.api.account.calls.create(
        to=call.recipient_number, # call recipient first
        from_='+16197276734', # this is our Twilio phone number
        url='http://{}{}'.format(request.META['HTTP_HOST'],
                                 reverse('connect_endpoint', args=[call.id])))
    return redirect(reverse('call_status', args=[call.id]))

@csrf_exempt
@require_http_methods(["POST"])
def connect(request, call_id):
    call = TwilioCall.objects.get(id=call_id)
    if call is None:
        return HttpResponseNotFound('error: call not found.')
    call.begin_call()
    return render(request, 'twilio_caller/call.xml', { 'call': call })

class ProcessRecordingAfterHttpResponse(HttpResponse):
    '''Send HttpResponse and then download & process Twilio call.

    This is really only to be used when returning responses for the
    <Dial recordingStatusCallback="..."> element in TwiML.

    If generally doing things after returning HTTP responses is
    useful, this class can be abstracted into a more general class for
    that (RunAfterHttpResponse or something).  But I suspect at that
    point it's actually better to have some offline work queue.
    '''
    def __init__(self, twilioData={}, *args, **kwargs):
        super(ProcessRecordingAfterHttpResponse, self).__init__(*args, **kwargs)
        self.twilioData = twilioData

    def close(self):
        super(ProcessRecordingAfterHttpResponse, self).close()
        r = requests.get(self.twilioData['RecordingUrl'])
        print('---- response to downloading recording ----')
        pprint(r.headers)

        if r.headers['Content-Type'] != 'audio/x-wav':
            raise Exception('can only handle MIME type audio/x-wav, not {}'.format(r.headers['Content-Type']))


        recording_path = '/tmp/twilio_{}.wav'.format(
            self.twilioData['RecordingSid'])
        with open(recording_path, 'wb') as f:
            f.write(r.content)
            print('saved to {}'.format(recording_path))

        base = path.basename(recording_path)
        key = base.split('.')[0]

        db = None
        if HACK_DB:
            with open(HACK_DB, 'r') as f:
                db = json.loads(f.read())
                if key not in db['audio']:
                    db['audio'][key] = {}



        client = storage.Client()
        bucket = client.get_bucket('illiad-audio')

        if UPLOAD_ORIGINAL:
            print("Uploading original file to cloud")
            blob = bucket.blob(base)
            with open(recording_path, 'rb') as f:
                blob.upload_from_file(f)
            #TODO: need to figure out secure way of actually doing this
            blob.make_public()
            url = blob.public_url
            if db:
                db['audio'][key]['aws_url'] = url
                with open(HACK_DB, 'w') as f:
                    f.write(json.dumps(db))
                    print("original url saved")

        if DO_INDEXING:
            print("Indexing file")
            deepgram_id = index_audio_url(url)
            if db:
                db['audio'][key]['deepgram_id'] = deepgram_id
                with open(HACK_DB, 'w') as f:
                    f.write(json.dumps(db))
                    print("Deepgram ID saved")
        if DO_TRANSCRIPTS:
            #TODO: delete original from local filesystem
            print("slicing file")
            slice_dir = audio_tools.slice_wav_file(recording_path)
            print("uploading sliced folder")
            blob_names = upload_folder(path.dirname(slice_dir), folder=path.basename(slice_dir))
            print("done uploading slices, finding transcript")
            words = transcribe_in_parallel(blob_names, name=self.twilioData['RecordingSid'])
            print('------ transcription ------')
            pprint(words)
            #TODO: delete slices from server
            print("uploading transcript to gcloud")
            transcript_blob = bucket.blob("{}_transcript.json".format(self.twilioData['RecordingSid']))
            transcript_blob.upload_from_string(json.dumps(words))
            print("done uploading transcript")
            if db:
                db['audio'][key]['transcript'] = words
                with open(HACK_DB, 'w') as f:
                    f.write(json.dumps(db))
                    print("saved transcript")
        print("FINISHED CALL %s"% self.twilioData['RecordingSid'])




@csrf_exempt
@require_http_methods(["POST"])
def record_callback(request, call_id):
    print('---- received record callback for call #{} ----'.format(call_id))
    pprint(request.POST)
    call = TwilioCall.objects.get(id=call_id)
    if call is None:
        return HttpResponseNotFound('error: call not found.')
    call.end_call(request.POST)
    return ProcessRecordingAfterHttpResponse(twilioData=request.POST,
                                             content='success') # 200 for Twilio

def status(request, call_id):
    call = TwilioCall.objects.get(id=call_id)
    if call is None:
        return HttpResponseNotFound('error: call not found.')
    return render(request, 'twilio_caller/status.html', { 'call': call })


def viewer(request, key):
    keywords = {}
    transcript_type = request.GET.get('transcript_type','transcript')

    content_id = mem_db['audio'][key]['deepgram_id']
    if request.method == "POST":
        keyword = request.POST['search-term']
        print("searching for %s"%keyword)
        keyword_results = audio_search(content_id, keyword)
        print("got keyword results")
        print(keyword_results)
        print("deepgram ID:")
        print(content_id)

        for i, confidence in enumerate(keyword_results['P']):
            keywords[str(i)] = {}
            keywords[str(i)]['starttime'] = keyword_results['startTime'][i]
            keywords[str(i)]['hex_confidence'] = confidence_to_hex(confidence)

    lines = generate_speaker_lines(sort_words(mem_db['audio'][key][transcript_type]))
    audio_url = mem_db['audio'][key]['aws_url']
    print("rendering with keywords")
    print(keywords)
    return render(request, 'twilio_caller/audio_page.html', {"lines":lines, "audio_key":key, "audio_url":audio_url,
                           "keywords":keywords})

