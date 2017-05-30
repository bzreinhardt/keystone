#import matplotlib
import numpy as np
import soundfile as sf
import scipy.io.wavfile as wavfile
import pdb
import os

path="/Users/Zaaron/Data/audio/ben_noah_5_23.wav"

# division time heurisitc in seconds
SILENCE = 0.5 #seconds
HRESHOLD = 50

rate, data = wavfile.read(path)



def contiguous_regions(condition):
    """Finds contiguous True regions of the boolean array "condition". Returns
    a 2D array where the first column is the start index of the region and the
    second column is the end index."""

    # Find the indicies of changes in "condition"
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
    midpoints = np.array([int(np.mean(group)) for group in groups])
    #pdb.set_trace()
    return midpoints

def find_divisions(audio, silence_sec, rate, threshold=50):
    """
    creates division points for multi-channel audio based on silences
    silence is the min amount of silence
    """
    silence = int(rate * silence_sec)
    #pdb.set_trace()
    all_midpoints = []
    for channel in range(0, audio.shape[1]):
        silent_regions = contiguous_regions(audio[:, channel] < threshold)
        long_enough = (silent_regions[:,1] - silent_regions[:,0] > silence)
        # this is going to be an nx2 array of the long silent regions
        long_regions = silent_regions[long_enough, :]
        #pdb.set_trace()
        midpoints = list(find_unique_midpoints(((long_regions[:,1]-long_regions[:,0])/2 + long_regions[:,0]).astype("int32")))
        all_midpoints.append(midpoints)
    return all_midpoints



all_midpoints = find_divisions(data, SILENCE, rate)
print("Number of found midpoints is \n"
      "channel1: %d \n"
      "channel2: %d \n" % (len(all_midpoints[0]), len(all_midpoints[2])))
directory, file = os.path.split(path)
name = file.split(".")[0]
flac_dir = "%s/%s_split"%(directory,name)
if not os.path.isdir(flac_dir):
    os.mkdir(flac_dir)
for i, channel in enumerate(all_midpoints):
    for j, midpoint in enumerate(channel):
        if j is 0:
            slice = data[0: midpoint]
        elif j is len(channel) - 1:
            slice = data[midpoint:-1]
        else:
            slice = data[channel[i-1]:midpoint]
        time_in_sec = float(midpoint)/float(rate)
        outfile = "%s/%s_channel_%d_timestamp_%d.flac"%(flac_dir, name, i, int(100*time_in_sec))
        sf.write(outfile, slice, rate)