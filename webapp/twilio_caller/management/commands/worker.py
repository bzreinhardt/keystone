from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from twilio_caller.models import TwilioCall

import boto3
from time import sleep
from os import unlink
import json
from datetime import datetime

from audio_pipeline import run_audio_pipeline

def timestamp():
    return datetime.now().isoformat()

class Command(BaseCommand):
    help = 'Background worker process for processing audio files'

    def handle(self, *args, **options):
        sqs = boto3.resource('sqs')
        recording_queue = sqs.get_queue_by_name(
            QueueName=settings.RECORDING_QUEUE)

        while True:
            messages = recording_queue.receive_messages(MaxNumberOfMessages=1)
            if len(messages) == 0:
                sleep(1)
                continue
            m = json.loads(messages[0].body)
            if m['type'] == 'uberconf_recording':
                print('{} - new message'.format(timestamp()))
                recording_path = m['data']['tmpfile_path']
                phrases = m['data']['phrases']
                call = TwilioCall.objects.get(id=m['data']['call_id'])
                success, key = run_audio_pipeline(recording_path, call,
                                                  do_indexing=True,
                                                  upload_original=True,
                                                  do_transcripts=False,
                                                  create_clips=True,
                                                  phrases=phrases,
                                                  min_confidence=0.4)
                if success:
                    call.keyword_state = TwilioCall.KEYWORDS_INDEXED
                    call.save()
                    messages[0].delete()
                    unlink(recording_path)
                else:
                    print('{} - worker error'.format(timestamp()))
            sleep(1)
