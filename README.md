Readme.md

Requirements:
speech_credentials.py file
install the speech_recognition python library

Modify speech_recognition to pass more paramters to IBM - this is in the __init__.py file in the speech_recognition folder
A couple of different ways to modify:

#For Basic timestamps with heatmap
        url = "https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?{}".format(urlencode({
            "profanity_filter": "false",
            "word_confidence": "true",
            "timestamps": "true",
            "continuous": "true",
            "model": "{}_BroadbandModel".format(language),
        }))

#To include speaker labels
        url = "https://stream.watsonplatform.net/speech-to-text/api/v1/recognize?{}".format(urlencode({
            "profanity_filter": "false",
            "word_confidence": "true",
            "timestamps": "true",
            "speaker_labels": "true",
            "continuous": "true",
            "model": "{}_NarrowbandModel".format(language),
        }))



This is a partial speech_credential file:
_
IBM_USERNAME = "xxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" # IBM Speech to Text usernames are strings of the form XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
IBM_PASSWORD = "xxxxxxxxxxxx" # IBM Speech to Text passwords are mixed-case alphanumeric strings

IBM_NLU_USERNAME = "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" # IBM Speech to Text usernames are strings of the form XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
IBM_NLU_PASSWORD = "xxxxxxxxx" # IBM Speech to Text passwords are mixed-case alphanumeric strings

GOOGLE_CLIENT_ID = "xxxxxxxxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "xxxxxxxxx"
GOOGLE_API_KEY = "xxxxxxxxxxxxxxx"

BING_KEY = "xxxxxxxxxxxxxxxx" # Microsoft Bing Voice Recognition API keys 32-character lowercase hexadecimal strings

