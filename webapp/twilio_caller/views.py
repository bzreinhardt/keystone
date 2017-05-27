from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from twilio.rest import Client as Twilio
from os import environ
from os import path
import sys

import requests

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
        to=orig, from_=dest, # 
        url="http://"+request.META['HTTP_HOST']+"/twilio_caller/connect_endpoint")
    return HttpResponse('Making call to {} now...'.format(dest))

@csrf_exempt
@require_http_methods(["POST"])
def connect(request):
    return render(request, 'twilio_caller/call.xml')

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
        
        wav_to_flac(recording_path)

        

@csrf_exempt
@require_http_methods(["POST"])
def record_callback(request):
    print('---- received record callback ----')
    pprint(request.POST)
    return ProcessRecordingAfterHttpResponse(twilioData=request.POST,
                                             content='success') # 200 for Twilio
