import math
import sys

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