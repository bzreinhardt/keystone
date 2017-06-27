import math
import sys
import re
import requests

def progress_bar(current_val, max_val, fraction=1, text=""):
    percent_done = int(float(current_val)/float(max_val)*100.)
    num_bars = int(math.floor(percent_done/5.))
    sys.stdout.write('\r')
    # the exact output you're looking for:
    if current_val != max_val:
        sys.stdout.write("[%-20s] %s%d/%d" % ('='*num_bars, text, current_val, max_val))
    else:
        sys.stdout.write("[%-20s] %s%d/%d\n" % ('=' * num_bars, text, current_val, max_val))
    sys.stdout.flush()


def phone_number_parser(phone_number):
    """
    Processes a phone number into a twilio-friendly number
    :param phone_number: string ideally of digits
    :return: a phone number in a "###########" format
    """
    # Assuming only american phone calls
    # Conditions
    # phone_number[0] = 1
    # len(phone_number) == 11
    #
    condition = re.compile(r'[^\d]+')
    number = condition.sub('', phone_number)
    if len(number) is 7:
        return ValueError("Phone numbers need an area code!")
    if len(number) < 10 or len(number) > 12:
        return ValueError("Phone number badly formatted: needs to have three digit area code and "
                          " seven other digits")
    if len(number) is 10:
        number = "1" + number
    return number

def send_simple_message(to='notes@evoke.ai', subject='evoke notification!', text='no text entered'):
    return requests.post(
        "https://api.mailgun.net/v3/sandbox0999fe079ff549b2bddaaa6e2c81ec2a.mailgun.org/messages",
        auth=("api", "key-180e3e48d159f0bc57fc104e291a2417"),
        data={"from": "Mailgun Sandbox <postmaster@sandbox0999fe079ff549b2bddaaa6e2c81ec2a.mailgun.org>",
              "to": to,
              "subject": subject,
              "text":text})

def remove_bad_chars(str):
    pattern = re.compile('[\W_]+')
    return pattern.sub('', str)



