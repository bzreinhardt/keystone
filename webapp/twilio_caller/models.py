from django.db import models
from django.utils import timezone
from django.conf import settings

class TwilioCall(models.Model):
    caller_name = models.TextField()
    caller_email = models.TextField()
    caller_number = models.TextField()
    recipient_name = models.TextField()
    recipient_email = models.TextField()
    recipient_number = models.TextField()
    
    call_begin = models.DateTimeField(blank=True, null=True)
    call_end = models.DateTimeField(blank=True, null=True)
    
    twilio_sid = models.TextField(blank=True, null=True)
    twilio_recording_sid = models.TextField(blank=True, null=True)
    twilio_recording_url = models.TextField(blank=True, null=True)

    recording_url = models.TextField(blank=True, null=True)
    audio_index_id = models.TextField(blank=True, null=True)
    transcript = models.TextField(blank=True, null=True)
    #TODO: create a setter/getter for this because it should be a dictionary
    phrases = models.TextField(blank=True, null=True)
    phrase_results = models.TextField(blank=True, null=True)
    min_confidence = models.FloatField(blank=True, null=True)

    CALL_STATES = (
        ('NI', 'Not Initiated'),
        ('CP', 'Call in Progress'),
        ('CF', 'Call Finished'),
        ('TP', 'Transcription in Progress'),
        ('TC', 'Transcription Complete'),
    )

    NOT_INITIATED = 'NI'
    CALL_IN_PROGRESS = 'CP'
    CALL_FINISHED = 'CF'
    TRANSCRIPTION_IN_PROGRESS = 'TP'
    TRANSCRIPTION_COMPLETE = 'TC'

    state = models.CharField(max_length=2, choices=CALL_STATES,
                             default=NOT_INITIATED)

    def begin_call(self):
        assert self.state == self.NOT_INITIATED
        self.call_begin = timezone.now()
        self.state = self.CALL_IN_PROGRESS
        self.save()

    def end_call(self, twilio_data):
        if not settings.DEBUG:
            assert self.state == self.CALL_IN_PROGRESS
        self.call_end = timezone.now()
        self.state = self.CALL_FINISHED
        self.twilio_sid = twilio_data['CallSid']
        self.twilio_recording_sid = twilio_data['RecordingSid']
        self.twilio_recording_url = twilio_data['RecordingUrl']
        self.save()

    def begin_transcription(self):
        assert self.state == self.CALL_FINISHED
        self.state = self.TRANSCRIPTION_IN_PROGRESS
        self.save()

    def finish_transcription(self):
        assert self.state == self.TRANSCRIPTION_IN_PROGRESS
        self.state = self.TRANSCRIPTION_COMPLETE
        self.save()

    def __str__(self):
        if (not self.call_begin) and (not self.call_end):
            return '<Call did not take place>'

        if self.call_begin and not self.call_end:
            return '<Call from {} to {} currently in progress>'.format(
                self.caller_name, self.recipient_name)
        
        return 'Call from {} to {} at {} on {}.'.format(
            self.caller_name, self.recipient_name,
            self.call_begin.strftime('%H:%M'),
            self.call_begin.strftime('%d/%m/%Y'))
