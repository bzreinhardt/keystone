#!/usr/bin/env python

# This file is just to help test/debug SQS worker.  Make sure there's
# actually a recording at tmpfile_path.

import boto3
import time
import json
from pprint import pprint

RECORDING_QUEUE = 'noah-0'

sqs = boto3.resource('sqs')
recording_queue = sqs.get_queue_by_name(QueueName=RECORDING_QUEUE)

recording_queue.send_message(MessageBody=json.dumps({
    'type': 'uberconf_recording',
    'data': {
        'call_id': 8,
        'phrases': {
            'action item': {'type': 'after'},
            'deadline': {'type': 'after'},
            'prototype': {'type': 'after'}
        },
        'tmpfile_path': '/tmp/AMIfv964IIrOj2o3VLfhxEPDnI6kBDFVMQQxsL5COdy1jkxAYHr1GTp_gYdjHpMzzT7uO6V9yyUg6twQjdYdJJ7mtBVWaVPgxyTMQZB2kGDK7R-X2bd47_k5Y46E_BskWF6gMjOaI01yaS2wk_E5EF2H25DFVldJOA.mp3',
        'twilio_recording_sid': 'AMIfv964IIrOj2o3VLfhxEPDnI6kBDFVMQQxsL5COdy1jkxAYHr1GTp_gYdjHpMzzT7uO6V9yyUg6twQjdYdJJ7mtBVWaVPgxyTMQZB2kGDK7R-X2bd47_k5Y46E_BskWF6gMjOaI01yaS2wk_E5EF2H25DFVldJOA'
    },
}))
