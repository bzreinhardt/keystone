from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
#from django.contrib.sites.models import Site
from django.conf import settings
from twilio.rest import Client as Twilio
from django import forms
from os import environ
from os import path
from os import unlink
import random
import shutil
import sys
import json
import re
import string

import requests

from google.cloud import storage

from twilio_caller.models import TwilioCall
from utility import phone_number_parser

# TODO: https://stackoverflow.com/a/3856947/554487
sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
import audio_tools
from keystone_asr import wav_to_flac, transcribe_gcs, upload_folder, transcribe_slices, transcribe_in_parallel
from pprint import pprint
from keyword_search import index_audio_url, audio_search, phrase_search
from keystone import generate_speaker_lines, sort_words, confidence_to_hex, add_speakers

twilio = Twilio(environ.get('TWILIO_ACCOUNT_SID'),
                environ.get('TWILIO_AUTH_TOKEN'))

UPLOAD_ORIGINAL = True
DO_TRANSCRIPTS = True
DO_INDEXING = True
DO_PHRASE_DETECTION = True

class ReusableForm(forms.Form):
    name = forms.CharField(label='Name:', max_length=100)


def index(request):
    return render(request, 'twilio_caller/callform.html')


@require_http_methods(["POST"])
def call(request):
    call = TwilioCall.objects.create(
        caller_name=request.POST['caller-name'],
        caller_email=request.POST['caller-email'],
        caller_number=phone_number_parser(request.POST['caller-number']),
        recipient_name=request.POST['recipient-name'],
        recipient_email=request.POST['recipient-email'],
        recipient_number=phone_number_parser(request.POST['recipient-number']))
    call.save()

    phrases = request.POST['phrases'].split(";")
    call.phrases = json.dumps(phrases)



    generate_transcript = 'transcript' in request.POST.keys()
    min_confidence = request.POST['min_confidence']
    if len(min_confidence) == 0:
        min_confidence = 0.3
    min_confidence = float(min_confidence)
    call.min_confidence = min_confidence
    call.save()
    #import pdb
    #pdb.set_trace()
    if request.method == 'POST' and request.FILES['myfile']:
        pattern = re.compile('[\W_]+')
        myfile = request.FILES['myfile']
        name, file_extension = path.splitext(myfile.name)
        name = pattern.sub('', name)
        filename = '/tmp/%s%s' % (name, file_extension)
        with open(filename, 'wb') as f:
            for chunk in myfile.chunks():
                f.write(chunk)
        call.twilio_recording_sid= name + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        call.save()
        success, key = run_audio_pipeline(filename, call,
                                          do_indexing=True,
                                          upload_original=True,
                                          do_transcripts=generate_transcript,
                                          phrases=phrases)
        call.call_end = timezone.now()
        call.state = call.CALL_FINISHED
        call.save()
        if success:
            unlink(filename)

    else:
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


def send_simple_message(to='bzreinhardt@gmail.com', subject='evoke notification!', text='no text entered'):
    return requests.post(
        "https://api.mailgun.net/v3/sandbox0999fe079ff549b2bddaaa6e2c81ec2a.mailgun.org/messages",
        auth=("api", "key-180e3e48d159f0bc57fc104e291a2417"),
        data={"from": "Mailgun Sandbox <postmaster@sandbox0999fe079ff549b2bddaaa6e2c81ec2a.mailgun.org>",
        "to": to,
        "subject": subject,
        "text":text})


def run_audio_pipeline(recording_path, call, upload_original=False,
                       do_indexing=False, do_transcripts=False, phrases=[],
                       min_confidence=0.4):
    key = call.twilio_recording_sid
    base = path.basename(recording_path)

    client = storage.Client()
    bucket = client.get_bucket('illiad-audio')

    if upload_original:# and call.recording_url is '':
        print("Uploading original file to cloud")
        blob = bucket.blob(base)
        with open(recording_path, 'rb') as f:
            blob.upload_from_file(f)
        # TODO: need to figure out secure way of actually doing this
        blob.make_public()
        url = blob.public_url
        call.recording_url = url
        call.save()

    if do_indexing:# and call.audio_index_id is '':
        print("Indexing file")
        deepgram_id = index_audio_url(call.recording_url)
        call.audio_index_id = deepgram_id
        call.save()
        index_ready = False
        while not index_ready:
            test = audio_search(call.audio_index_id, 'test')
            if test['error'] is None:
                index_ready = True
        if len(phrases) > 0:
            phrase_times = {}
            for phrase in phrases:
                if len(phrase) == 0:
                    continue
                times = audio_search(call.audio_index_id, phrase, min_confidence=min_confidence)
                if len(times) > 0:
                    phrase_times[phrase] = times
            call.phrase_results = json.dumps(phrase_times)
            call.save()

    if do_transcripts:
        # TODO: delete original from local filesystem
        print("slicing file")
        slice_dir = audio_tools.slice_wav_file(recording_path)
        print("uploading sliced folder")
        blob_names = upload_folder(path.dirname(slice_dir), folder=path.basename(slice_dir))
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

    print("FINISHED CALL %s" % key)
    display_url = "%s/alpha/viewer/%s/"%("www.evoke.ai", call.twilio_recording_sid)
    email_text = "Finished processing audio for %s. Results are available at %s" % (call.caller_name, display_url)
    send_simple_message(subject='audio pipeline complete!', text= email_text )
    if call.caller_email:
        send_simple_message(to=caller_email, subject='Evokation Complete!', text=email_text)
    return (True, key)




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
        key = self.twilioData['RecordingSid']
        call = TwilioCall.objects.get(twilio_recording_sid=key)
        success, key = run_audio_pipeline(recording_path,
                                          call,
                                          do_indexing=True,
                                          upload_original=True,
                                          do_transcripts=True,
                                          phrases=json.loads(call.phrases))
        if success:
            unlink(recording_path)

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
    call = TwilioCall.objects.get(twilio_recording_sid=key)
    content_id = call.audio_index_id
    if request.method == "POST":
        keyword = request.POST['search-term']
        print("searching for %s"%keyword)
        keyword_results = audio_search(content_id, keyword)
        print("got keyword results")
        print(keyword_results)
        print("deepgram ID:")
        print(content_id)
        if keyword_results['error']:
            keywords['0'] = {}
            keywords['0']['starttime'] = 'Sorry, we are still crunching your conversation. Check back in a minute'
        elif len(keyword_results['P']) == 0:
            keywords['0'] = {}
            keywords['0']['starttime'] = "No Results"
        else:
            for i, confidence in enumerate(keyword_results['P']):
                keywords[str(i)] = {}
                keywords[str(i)]['starttime'] = keyword_results['startTime'][i]
                keywords[str(i)]['hex_confidence'] = confidence_to_hex(confidence)
    if call.transcript:
        transcript = json.loads(call.transcript)
    else:
        transcript = []
    import pdb
    #pdb.set_trace()
    speakers = [call.recipient_name, call.caller_name]
    transcript = add_speakers(transcript, speakers)
    lines = generate_speaker_lines(sort_words(transcript))
    audio_url = call.recording_url
    phrases = {}
    bad_phrases = ['', ' ']
    if call.phrase_results:
        phrase_results = json.loads(call.phrase_results)

        for phrase in phrase_results:
            if phrase in bad_phrases:
                continue
            phrases[phrase] = {'times':[]}
            for i, time in enumerate(phrase_results[phrase]['startTime']):
                phrases[phrase]['times'].append({'time':phrase_results['startTime'][i],
                                                 'confidence':phrase_results['P'][i]})
    print("rendering with keywords")
    print(keywords)
    return render(request, 'twilio_caller/audio_page.html', {"lines":lines, "audio_key":key, "audio_url":audio_url,
                           "keywords":keywords, "phrases":phrases})

def simple_upload(request):
    if request.method == 'POST' and request.FILES['myfile']:
        pattern = re.compile('[\W_]+')
        myfile = request.FILES['myfile']
        name, file_extension = path.splitext(myfile.name)
        name = pattern.sub('', name)
        filename = '/tmp/%s%s'%(name, file_extension)
        with open(filename, 'wb') as f:
            for chunk in myfile.chunks():
                f.write(chunk)
        if TwilioCall.objects.filter(twilio_recording_sid=name).exists():
            call = TwilioCall.objects.get(twilio_recording_sid=name)
        else:
            call = TwilioCall.objects.create(
                caller_name=request.POST['caller_name'],
                recipient_name=request.POST['recipient_name'],
                twilio_recording_sid=name)
        call.save()
        success, key = run_audio_pipeline(filename, call, do_indexing=True, upload_original=True)
        if success:
            shutil.rmtree(filename)
        return render(request, 'twilio_caller/upload.html', {
            'key': call.twilio_recording_sid
        })
        print("Successfully processed call %s"%key)
    return render(request, 'twilio_caller/upload.html')