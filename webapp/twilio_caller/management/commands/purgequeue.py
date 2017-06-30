from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import boto3

class Command(BaseCommand):
    def handle(self, *args, **options):
        confirmation = input('about to purge queue {}; continue? [y/n]  '.format(settings.RECORDING_QUEUE))
        if confirmation not in ['y', 'Y', 'yes', 'Yes', 'YES']:
            print('aborting.')
            return
        sqs = boto3.resource('sqs')
        queue = sqs.get_queue_by_name(QueueName=settings.RECORDING_QUEUE)
        queue.purge()

