from django.shortcuts import render, redirect
from django.utils import timezone
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from main.models import PotentialEmail
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


def index(request):
  if request.method == "POST":
    email = request.POST['email']
    print("got email %s" % email)
    potential_email = PotentialEmail(email=email)
    potential_email.save()
    print("saved email")
    return render(request, 'main/thank_you.html')
  return render(request, 'main/landing_page.html')

@require_http_methods(["POST"])
def submit(request):
    email = request.POST['email']
    print("got email %s"%email)
    potential_email = PotentialEmail(email=email)
    potential_email.save()