from django.shortcuts import render
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from twilio.rest import Client as Twilio
from os import environ
from os import path
import sys

import requests

from google.cloud import storage

# TODO: https://stackoverflow.com/a/3856947/554487
sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
from keystone_asr import wav_to_flac, transcribe_gcs
from pprint import pprint

twilio = Twilio(environ.get('TWILIO_ACCOUNT_SID'),
                environ.get('TWILIO_AUTH_TOKEN'))

def index(request):
    return render(request, 'twilio_caller/callform.html')

@require_http_methods(["POST"])
def call(request):
    orig, dest = request.POST['orig'], request.POST['dest']
    twilio.api.account.calls.create(
        to=orig, from_='+16197276734', # this is our Twilio phone number
        url='http://{}{}'.format(request.META['HTTP_HOST'],
                                 reverse('connect_endpoint', args=[dest])))
    return HttpResponse('Making call to {} now...'.format(dest))

@csrf_exempt
@require_http_methods(["POST"])
def connect(request, number_to_connect):
    return render(request, 'twilio_caller/call.xml',
                  { 'number_to_connect': number_to_connect })

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

        recording_path = '/Users/noah/tmp/twilio_{}.wav'.format(
            self.twilioData['RecordingSid'])
        with open(recording_path, 'wb') as f:
            f.write(r.content)
            print('saved to {}'.format(recording_path))
        
        lpath, rpath = wav_to_flac(recording_path)

        print(' left channel saved at ' + lpath)
        print('right channel saved at ' + rpath)

        client = storage.Client()
        bucket = client.get_bucket('illiad-audio')
        print('uploading left channel...')
        lbase = path.basename(lpath)
        lblob = bucket.blob(lbase)
        with open(lpath, 'rb') as f:
            lblob.upload_from_file(f)
        print('done uploading left channel. now uploading right channel...')
        rbase = path.basename(rpath)
        rblob = bucket.blob(rbase)
        with open(rpath, 'rb') as f:
            rblob.upload_from_file(f)
        print('done uploading right channel. now transcribing left channel...')
        lwords = transcribe_gcs('gs://illiad-audio/' + lbase)
        print('done transcribing left channel. now transcribing right channel...')
        rwords = transcribe_gcs('gs://illiad-audio/' + rbase)
        print('---- transcription: right ----')
        pprint(lwords)
        print('---- transcription: left ----')
        pprint(rwords)

@csrf_exempt
@require_http_methods(["POST"])
def record_callback(request):
    print('---- received record callback ----')
    pprint(request.POST)
    return ProcessRecordingAfterHttpResponse(twilioData=request.POST,
                                             content='success') # 200 for Twilio
