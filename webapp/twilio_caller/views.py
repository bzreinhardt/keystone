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
from os import unlink
import random
import shutil
import sys
import json
import re
import string

import requests
import boto3

from google.cloud import storage

from twilio_caller.models import TwilioCall
from utility import phone_number_parser, send_simple_message
from audio_pipeline import run_audio_pipeline

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
DO_TRANSCRIPTS = False
DO_INDEXING = True
DO_PHRASE_DETECTION = True
NUM_KEYWORDS = 4
DEFAULT_PHRASE_TIME_SEC=15
BAD_PHRASES = ['', ' ']

sqs = boto3.resource('sqs')
print('using queue: {}'.format(settings.RECORDING_QUEUE))
recording_queue = sqs.get_queue_by_name(QueueName=settings.RECORDING_QUEUE)

class ReusableForm(forms.Form):
    name = forms.CharField(label='Name:', max_length=100)


def index(request):
    return render(request, 'twilio_caller/callform.html')


@require_http_methods(["POST"])
def call(request):
    # First make sure the caller has a verified number
    number = phone_number_parser(request.POST['caller-number'])
    caller_ids = twilio.outgoing_caller_ids.list(phone_number=number)
    if len(caller_ids) == 0:
        code = twilio.validation_requests.create(number)
        return render(request, 'twilio_caller/callform.html', {
            'code':code.validation_code,
            'caller_name':request.POST['caller-name'],
            'caller_email':request.POST['caller-email'],
            'caller_number':number,
            'recipient_name':request.POST['recipient-name'],
            'recipient_email':request.POST['recipient-email'],
            'recipient_number':
                phone_number_parser(request.POST['recipient-number'])})

    call = TwilioCall.objects.create(
        caller_name=request.POST['caller-name'],
        caller_email=request.POST['caller-email'],
        caller_number=phone_number_parser(request.POST['caller-number']),
        recipient_name=request.POST['recipient-name'],
        recipient_email=request.POST['recipient-email'],
        recipient_number=phone_number_parser(request.POST['recipient-number']))
    # Make sure the call always has a name
    if call.caller_name is None:
        call.caller_name = call.caller_number
    if call.recipient_name is None:
        call.recipient_name = call.recipient_number
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

@csrf_exempt
@require_http_methods(["POST"])
def record_callback(request, call_id):
    print('---- received record callback for call #{} ----'.format(call_id))
    pprint(request.POST)
    call = TwilioCall.objects.get(id=call_id)
    if call is None:
        return HttpResponseNotFound('error: call not found.')
    call.end_call(request.POST)
    recording_queue.send_message(MessageBody=json.dumps({
                'type': 'twilio_call',
                'data': { 'twilio_rec': request.POST,
                          'force_indexing': False,
                          'force_upload': False,
                          'force_transcript': False
                        },
                }))
    return HttpResponse('success') # 200 for Twilio

def status(request, call_id):
    call = TwilioCall.objects.get(id=call_id)
    if call is None:
        return HttpResponseNotFound('error: call not found.')
    return render(request, 'twilio_caller/status.html', { 'call': call })

def call_from_upload(request_file):
    pass

def upload_uberconf(request):
    if request.method == 'POST':
        upload = request.FILES['recording']
        tmpfile = path.join('/tmp', upload.name.replace(' ', ''))
        with open(tmpfile, 'wb') as f:
            for chunk in upload.chunks():
                f.write(chunk)
        name, extension = path.splitext(upload.name)
        if TwilioCall.objects.filter(twilio_recording_sid=name).exists():
            call = TwilioCall.objects.get(twilio_recording_sid=name)
        else:
            call = TwilioCall.objects.create(twilio_recording_sid=name)
        phrases = {kw.strip(): {'type': 'after'}
                   for kw in request.POST['keywords'].split(',')}
        call.phrases = json.dumps(phrases)
        call.participants = request.POST['participants']
        # Set the people in the call to be the to and from of the call
        participants=request.POST['participants'].split(',')
        if len(participants) > 0:
            call.caller_name = participants[0]
        else:
            call.caller_name = 'unknown'
        if len(participants) > 1:
            call.recipient_name = participants[1]
        else:
            call.recipient_name = 'unknown'
        call.call_begin = timezone.now()


        call.keyword_state = TwilioCall.RECORDING_UPLOADED
        call.save()
        recording_queue.send_message(MessageBody=json.dumps({
            'type': 'uberconf_recording',
            'data': {
                'call_id': call.id,
                'twilio_recording_sid': call.twilio_recording_sid,
                'tmpfile_path': tmpfile,
                'phrases': phrases,
                'force_indexing':False,
                'force_upload':False,
                'force_transcript':False,
            }
        }))
        return redirect(reverse('render_backend_viewer', args=[name]))
    else:
        return render(request, 'twilio_caller/upload_uberconf.html')

def notes(request, call_id):
    call = TwilioCall.objects.get(id=call_id)
    if call is None:
        return HttpResponseNotFound('error: call not found.')

    keywords = json.loads(call.phrase_results)
    phrases = [{'text': k,
                'items': list(filter(None, keywords[k].get('notes', [])))}
               for k in json.loads(call.phrases).keys()]

    return render(request, 'twilio_caller/notes.html', {
        'participants': 'Ben and Noah',
        'date': call.call_begin.strftime('%a %d %b %Y'),
        'phrases': phrases,
        })

def viewer(request, key, show_confidence=None):
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
    speakers = [call.recipient_name, call.caller_name]
    transcript = add_speakers(transcript, speakers)
    lines = generate_speaker_lines(sort_words(transcript))
    audio_url = call.recording_url
    print_phrases = {}
    if call.phrase_results:

        phrase_results = json.loads(call.phrase_results)

        phrases = json.loads(call.phrases)
        for phrase in phrase_results:
            if phrase in BAD_PHRASES:
                continue
            print_phrases[phrase] = {'times':[]}

            for i, time in enumerate(phrase_results[phrase]['startTime']):

                if phrase_results[phrase]['is_phrase'][i] is False or phrase_results[phrase]['is_phrase'][i] == 'False':
                    continue
                if phrases[phrase]['type']=='before':
                    starttime = time - DEFAULT_PHRASE_TIME_SEC
                    stoptime = time
                else:
                    starttime = time
                    stoptime = time - DEFAULT_PHRASE_TIME_SEC
                confidence = phrase_results[phrase]['P'][i]
                url = phrase_results[phrase]['slices'][i]
                hex_confidence = 0
                if show_confidence is not None:
                    hex_confidence = confidence_to_hex(confidence)
                out_dict = {'keytime':time,
                           'starttime' : starttime,
                           'stoptime' : stoptime,
                           'confidence': confidence,
                           'url': url,
                           'hex_confidence':hex_confidence}

                if 'notes' in phrase_results[phrase]:
                    out_dict['note'] = phrase_results[phrase]['notes'][i]
                for question in ['who', 'what', 'where', 'when', 'why']:
                    if question+"s" in phrase_results[phrase]:
                        if len(phrase_results[phrase][question+"s"][i]) > 0:
                            out_dict[question] = phrase_results[phrase][question+"s"][i]

                print_phrases[phrase]['times'].append(out_dict)

    return render(request, 'twilio_caller/audio_page.html', {
        "lines":lines, "audio_key":key, "audio_url":audio_url,
        "keywords":keywords, "phrases":print_phrases})


def backend_viewer(request, key):
    keywords = {}
    transcript_type = request.GET.get('transcript_type','transcript')
    call = TwilioCall.objects.get(twilio_recording_sid=key)
    content_id = call.audio_index_id

    if request.method == "POST":
        if 'keyword-submit' in request.POST:
            print("got keyword post")
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
        elif 'phrase-submit' in request.POST:
            if call.phrase_results:
                print("got phrase post")
                phrase_results = json.loads(call.phrase_results)
                phrases = json.loads(call.phrases)
                for phrase in phrase_results:
                    if phrase in BAD_PHRASES:
                        continue
                    is_phrase = []
                    whos = []
                    whats = []
                    wheres = []
                    whens = []
                    whys = []
                    notes = []
                    for time in phrase_results[phrase]['startTime']:
                        if "%s_%s_exists" % (phrase, time) in request.POST:
                            is_phrase.append(request.POST["%s_%s_exists" % (phrase, time)] == 'True')
                        else:
                            is_phrase.append(False)
                        if "%s_%s_note" % (phrase, time) in request.POST:

                            notes.append(request.POST["%s_%s_note" % (phrase, time)])
                        if "%s_%s_who" % (phrase, time) in request.POST:
                            whos.append(request.POST["%s_%s_who" % (phrase, time)])
                        if "%s_%s_what" % (phrase, time) in request.POST:
                            whats.append(request.POST["%s_%s_what" % (phrase, time)])
                        if "%s_%s_where" % (phrase, time) in request.POST:
                            wheres.append(request.POST["%s_%s_where" % (phrase, time)])
                        if "%s_%s_when" % (phrase, time) in request.POST:
                            whens.append(request.POST["%s_%s_when" % (phrase, time)])
                        if "%s_%s_why" % (phrase, time) in request.POST:
                            whys.append(request.POST["%s_%s_why" % (phrase, time)])
                    phrase_results[phrase]['is_phrase'] = is_phrase
                    phrase_results[phrase]['notes'] = notes
                    phrase_results[phrase]['whos'] = whos
                    phrase_results[phrase]['whats'] = whats
                    phrase_results[phrase]['wheres'] = wheres
                    phrase_results[phrase]['whens'] = whens
                    phrase_results[phrase]['whys'] = whys

                call.phrase_results = json.dumps(phrase_results)
                call.save()


    if call.transcript:
        transcript = json.loads(call.transcript)
    else:
        transcript = []
    speakers = [call.recipient_name, call.caller_name]
    transcript = add_speakers(transcript, speakers)
    lines = generate_speaker_lines(sort_words(transcript))
    audio_url = call.recording_url
    print_phrases = {}
    bad_phrases = ['', ' ']
    if call.phrase_results:
        phrase_results = json.loads(call.phrase_results)
        phrases = json.loads(call.phrases)
        for phrase in phrase_results:
            if phrase in BAD_PHRASES:
                continue
            print_phrases[phrase] = {'times':[]}
            for i, time in enumerate(phrase_results[phrase]['startTime']):
                if phrase not in phrases:
                    # this only happens when the file has been uploaded multiple
                    # times, with different phrase sets. Should only happen in
                    # dev and testing. We can safely ignore, for now.
                    continue
                if phrases[phrase]['type'] == 'before':
                    starttime = time - DEFAULT_PHRASE_TIME_SEC
                    stoptime = time
                else:
                    starttime = time
                    stoptime = time - DEFAULT_PHRASE_TIME_SEC
                confidence = phrase_results[phrase]['P'][i]
                url = phrase_results[phrase]['slices'][i]
                print_phrases[phrase]['times'].append({'keytime':time,
                                                       'starttime' : starttime,
                                                       'stoptime' : stoptime,
                                                       'confidence': confidence,
                                                       'url': url,
                                                       'hex_confidence':confidence_to_hex(confidence)})
    return render(request, 'twilio_caller/backend_audio_page.html', {
        "lines": lines, "audio_key": key, "audio_url": audio_url,
        "keywords": keywords, "phrases": print_phrases})

def clip_viewer(request, key):
    call = TwilioCall.objects.get(twilio_recording_sid=key)
    speakers = [call.recipient_name, call.caller_name]
    transcript = add_speakers(transcript, speakers)
    lines = generate_speaker_lines(sort_words(transcript))
    audio_url = call.recording_url
    print_phrases = {}
    bad_phrases = ['', ' ']
    if call.phrase_results:
        phrase_results = json.loads(call.phrase_results)
        phrases = json.loads(call.phrases)
        for phrase in phrase_results:
            if phrase in bad_phrases:
                continue
            print_phrases[phrase] = {'times': []}
            # pdb.set_trace()
            for i, time in enumerate(phrase_results[phrase]['startTime']):
                if phrases[phrase]['type'] == 'before':
                    starttime = time - DEFAULT_PHRASE_TIME_SEC
                    stoptime = time
                else:
                    starttime = time
                    stoptime = time - DEFAULT_PHRASE_TIME_SEC

                print_phrases[phrase]['times'].append({'starttime': starttime,
                                                       'stoptime': stoptime,
                                                       'confidence': confidence_to_hex(phrase_results[phrase]['P'][i])})
    print("rendering with keywords")
    print(keywords)
    return render(request, 'twilio_caller/backend_audio_page.html',
                  {"lines": lines, "audio_key": key, "audio_url": audio_url,
                   "keywords": keywords, "phrases": print_phrases})


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
