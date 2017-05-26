from django.db import models

# Create your models here.

class Call(models.Model):
    orig = models.CharField('phone # of caller', max_length=200)
    dest = models.CharField('phone # to be called', max_length=200)
    timestamp = models.DateTimeField('time of call')
