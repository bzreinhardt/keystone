from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from twilio_caller.models import TwilioCall

import boto3
from time import sleep
from os import unlink, path
import json
from datetime import datetime
from pprint import pprint

import requests

from audio_pipeline import run_audio_pipeline

def timestamp():
    return datetime.now().isoformat()

class Command(BaseCommand):
    '''Background worker process for processing audio files.

    The main loop, Command.handle, waits for incoming messages in the
    SQS queue.  It deserializes JSON messages, then calls the method
    with the name specified in the `type` field of the message with
    the arguments of the `data` field of the message.
    '''
    help = 'Background worker process for processing audio files'

    def handle(self, *args, **options):
        sqs = boto3.resource('sqs')
        recording_queue = sqs.get_queue_by_name(
            QueueName=settings.RECORDING_QUEUE)

        while True:
            print ("getting a message")
            messages = recording_queue.receive_messages(MaxNumberOfMessages=1)
            if len(messages) == 0:
                sleep(1)
                continue
            m = json.loads(messages[0].body)

            message_handler = getattr(self, m['type'], None)
            if callable(message_handler):
                try:
                    print("processing message:")
                    print(m['data'])
                    success = message_handler(**m['data'])
                    if success:
                        messages[0].delete()
                    # todo: else resend the message in half an hour
                except Exception as e:
                    print('ERROR PROCESSING MESSAGE: {}'.format(e))
                    pprint(m)
                    # todo: resend the message in half an hour
            else:
                print("No handler for message of type {}".format(m['type']))
            
            sleep(1)

    def uberconf_recording(self, *, call_id, twilio_recording_sid,
                           tmpfile_path, phrases, force_indexing, force_upload,
                    force_transcript):
        print('{} - new message'.format(timestamp()))
        call = TwilioCall.objects.get(id=call_id)
        success, key = run_audio_pipeline(tmpfile_path, call,
                                          do_indexing=force_indexing,
                                          upload_original=force_upload,
                                          do_transcripts=force_transcript,
                                          create_clips=True,
                                          phrases=phrases,
                                          min_confidence=0.4)
        if success:
            call.keyword_state = TwilioCall.KEYWORDS_INDEXED
            call.save()
            unlink(tmpfile_path)
            print('PROCESSED UBERCONF RECORDING {}'.format(twilio_recording_sid))
            return True
        else:
            print('{} - worker error'.format(timestamp()))
            return False

    def twilio_call(self, *, twilio_rec, phrases, force_indexing, force_upload,
                    force_transcript):
        r = requests.get(twilio_rec['RecordingUrl'])
        if r.headers['Content-Type'] != 'audio/x-wav':
            raise Exception('can only handle MIME type audio/x-wav, not {}' \
                                .format(r.headers['Content-Type']))
        sid = twilio_rec['RecordingSid']
        recording_path = '/tmp/twilio_{}.wav'.format(sid)
        with open(recording_path, 'wb') as f:
            f.write(r.content)
            print('saved to {}'.format(recording_path))

        call = TwilioCall.objects.get(twilio_recording_sid=sid)

        success, key = run_audio_pipeline(recording_path, call,
                                          do_indexing=force_indexing,
                                          upload_original=force_upload,
                                          do_transcripts=force_transcript,
                                          create_clips=True,
                                          phrases=phrases,
                                          min_confidence=0.4)
        if success:
            unlink(recording_path)
            print('PROCESSED CALL {}'.format(twilio_rec))
            return True
        else:
            print('ERROR PROCESSING CALL {}'.format(twilio_rec))
            return False
