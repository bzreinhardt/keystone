#import matplotlib
import numpy as np
import soundfile as sf
import scipy.io.wavfile as wavfile
import pdb
import os
import sys
import math
from utility import progress_bar

PATH="/Users/Zaaron/Downloads/InterviewAudio10.wav"

# division time heurisitc in seconds
SILENCE = 0.5 #seconds
THRESHOLD = 50
ENCODING_MULT_FACTOR= 100



def encode_filename(name, channel=None, timestamp=None, extension="flac"):
    out = name
    if channel is not None:
        out = out +"_channel_%d" % channel
    # Note that this means that we're only encoding timestamps to 100th of a second
    if timestamp == 0 or timestamp is not None:
        out = out + "_timestamp_%d" % int(timestamp * ENCODING_MULT_FACTOR)
    out = out + ".%s" % extension
    return out

def decode_filename(filepath):
    info = {}
    info["extension"] = os.path.basename(filepath).split(".")[-1]
    pieces = os.path.basename(filepath).split(".")[0].split("_")
    name = ""
    for i, piece in enumerate(pieces):
        if piece != "channel" and not "channel" in info:
            if i is 0:
                name += piece
            else:
                name += "_" + piece
        if piece == "channel":
            info["channel"] = int(pieces[i+1])
        if piece == "timestamp":
            info["timestamp"] = float(pieces[i+1])/100.0
    info["name"] = name
    return info

def contiguous_regions(condition):
    """Finds contiguous True regions of the boolean array "condition". Returns
    a 2D array where the first column is the start index of the region and the
    second column is the end index."""

    # Find the indicies of changes in "condition"
    condition = condition.astype(int)
    #pdb.set_trace()
    d = np.diff(condition)
    idx, = d.nonzero()

    # We need to start things after the change in "condition". Therefore,
    # we'll shift the index by 1 to the right.
    idx += 1

    if condition[0]:
        # If the start of condition is True prepend a 0
        idx = np.r_[0, idx]

    if condition[-1]:
        # If the end of condition is True, append the length of the array
        idx = np.r_[idx, condition.size] # Edit

    # Reshape the result into two columns
    idx.shape = (-1,2)
    return idx

def consecutive(data, stepsize=1):
    return np.split(data, np.where(np.diff(data) != stepsize)[0] + 1)

def find_unique_midpoints(midpoints_array, similarity_factor=0):
    """
    
    :param midpoints_array: 1xn array 
    :return: 1xn array
    """
    groups = consecutive(midpoints_array)
    if len(groups[0]) == 0:
        midpoints = np.array([])
    else:
        midpoints = np.array([int(np.mean(group)) for group in groups])
    return midpoints

def find_divisions(audio, silence_sec, rate, threshold=50):
    """
    creates division points for multi-channel audio based on silences
    silence is the min amount of silence
    """
    silence = int(rate * silence_sec)
    all_midpoints = []
    all_startpoints = []
    #pdb.set_trace()
    audio_shape = audio.shape
    if len(audio_shape) == 1:
        audio_shape = (1, 0)
    for channel in range(0, audio_shape[1]):
        silent_regions = contiguous_regions(audio[:, channel] < threshold)
        long_enough = ((silent_regions[:,1] - silent_regions[:,0]) > silence)
        # this is going to be an nx2 array of the long silent regions
        long_regions = silent_regions[long_enough, :]
        midpoints = list(find_unique_midpoints(((long_regions[:, 1]-long_regions[:, 0])/2 + long_regions[:, 0]).astype("int32")))
        startpoints = []
        for pair in zip([0] + midpoints, midpoints + [audio.shape[0]]):
            audio_start = np.argmax(audio[:, channel][pair[0]:pair[1]] > threshold) + pair[0]
            startpoints.append(audio_start)
        all_midpoints.append(midpoints)
        all_startpoints.append(startpoints)
    return all_midpoints, all_startpoints

def slice_wav_file(wav_file):

    rate, data = wavfile.read(wav_file)
    #pdb.set_trace()
    if len(data.shape) == 1:
        data = np.vstack((data,data)).T

    all_midpoints, all_startpoints = find_divisions(data, SILENCE, rate)
    print("Number of found midpoints is \n"
          "channel1: %d \n"
          "channel2: %d \n" % (len(all_midpoints[0]), len(all_midpoints[1])))
    directory, file = os.path.split(wav_file)
    name = file.split(".")[0]
    flac_dir = "%s/%s_split" % (directory, name)
    if not os.path.isdir(flac_dir):
        os.mkdir(flac_dir)

    for i, channel in enumerate(all_midpoints):

        for j, pair in enumerate(zip([0] + channel, channel + [data.shape[0]])):
            slice = data[pair[0]:pair[1], i]
            startpoint = all_startpoints[i][j]
            time_in_sec = float(startpoint) / float(rate)
            outfile = encode_filename(name, channel=i, timestamp=time_in_sec, extension="flac")
            progress_bar(j, len(channel)+1, "writing flac file: ")
            sf.write(os.path.join(flac_dir, outfile), slice, rate)
    return flac_dir

def slice_file(file):
    rate, data = sf.read(file)
    if len(data.shape) == 1:
        data = np.vstack((data,data)).T

    all_midpoints, all_startpoints = find_divisions(data, SILENCE, rate)
    print("Number of found midpoints is \n"
          "channel1: %d \n"
          "channel2: %d \n" % (len(all_midpoints[0]), len(all_midpoints[1])))
    directory, file = os.path.split(file)
    name = file.split(".")[0]
    flac_dir = "%s/%s_split" % (directory, name)
    if not os.path.isdir(flac_dir):
        os.mkdir(flac_dir)

    for i, channel in enumerate(all_midpoints):

        for j, pair in enumerate(zip([0] + channel, channel + [data.shape[0]])):
            slice = data[pair[0]:pair[1], i]
            startpoint = all_startpoints[i][j]
            time_in_sec = float(startpoint) / float(rate)
            outfile = encode_filename(name, channel=i, timestamp=time_in_sec, extension="flac")
            progress_bar(j, len(channel)+1, "writing flac file: ")
            sf.write(os.path.join(flac_dir, outfile), slice, rate)
    return flac_dir

def cut_file(file, start_time= 0, stop_time=10, out_file=None, split=False):
    #hack - should use magic to check filetype
    f, ext = os.path.splitext(file) 
    if ext == '.wav':
         rate, data = wavfile.read(file)
    else:
        rate, data = sf.read(file)

    start_time = float(start_time)
    stop_time = float(stop_time)
    extension = file.split(".")[-1]
    if len(data.shape) > 1:
        out = data[int(start_time*rate):int(stop_time*rate), :]
    else:
        out = data[int(start_time*rate):int(stop_time*rate)]
        channel = 0
    if split:
        for channel in range(0, out.shape[1]):

            out_split = out[:, channel]
            out_file = (os.path.basename(file)).split(".")[0] + "_%d_sec_channel_%d.%s"%(length_sec, channel, extension)
            out_file = os.path.join(os.path.dirname(file), out_file)
            sf.write(out_file, out_split, rate)
    else:
        if not out_file:
            out_file = (os.path.basename(file)).split(".")[0] + "_%d_sec_channel_%d.%s" % (length_sec, channel, extension)
            out_file = os.path.join(os.path.dirname(file), out_file)
        sf.write(out_file, out, rate)




if __name__=="__main__":
    cut_file(PATH, length_sec=120)
