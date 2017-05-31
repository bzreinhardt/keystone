import xmltodict
import os
from shutil import copyfile
from pydub import AudioSegment
import pdb

DATA_DIR = os.environ['DATA_DIR']
SERVER_STATIC_DIR = os.environ['KEYSTONE']+'/webapp/static'
SERVER_TEMPLATE_DIR = os.environ['KEYSTONE']+'/webapp/templates'

#def transcript_to_string


def mp3_to_wav(mp3_path):
    (path, filename) = os.path.split(mp3_path)
    if filename.split('.')[-1] != "mp3":
        return
    sound = AudioSegment.from_mp3(mp3_path)
    print ('eporting to %s/%s.wav' % (path, filename.split('.')[0]))
    sound.export("%s/%s.wav" % (path, filename.split('.')[0]), format="wav")
    return

def subsample_audio(file, start=0, stop=-1, out_file=''):
    format = os.path.split(file)[-1].split('.')[-1]
    sound = AudioSegment.from_file(file, format=format)
    if stop < 0:
        stop = len(sound)
    subsample = sound[start:stop]
    if len(out_file) > 0:
        subsample.export('out_file', format="wav")
    return subsample


def slice_audio_file(file, sample_length, export = False):
    format = os.path.split(file)[-1].split('.')[-1]
    sound = AudioSegment.from_file(file, format=format)
    subsamples = []
    for i in range(0, len(sound), sample_length):
        subsample = sound[i:i+sample_length]
        if export:
            name = "".join(file.split(".")[0:-1]) + "_%d.wav" % len(subsamples)
            subsample.export(name, format="wav")
        subsamples.append(subsample)
    return subsamples


def confidence_to_hex(confidence):
    return '#FF' + format(int(confidence * 255), 'x') + format(int(confidence * 255), 'x')


def generate_speaker_lines(words):
    lines = []
    previous_speaker = -1
    current_line = {"words":[]}
    for word in words:
        if 'confidence' not in word:
            word['confidence'] = 1.0
        word['hex_confidence'] = confidence_to_hex(word['confidence'])
        if previous_speaker is not word['speaker']:
            current_line['speaker'] = previous_speaker
            lines.append(current_line)
            current_line = {"words":[]}
        current_line['words'].append(word)
        previous_speaker = word['speaker']
    return lines

def compile_transcript(speaker_data):
    ### Compiles a transcript from a bunch of different speakers
    # Takes a list of speaker structures - dicts w/ field 'data' w/ fields 'id', 'starttime', 'endtime', 'text'

    # Keep track of a global timestamp
    time = 0
    # Keep track of index for each speaker data
    speaker_index = [0] * len(speaker_data)
    done_speakers = [False] * len(speaker_data)
    # Check to see if each speaker is talking
    # Set that person as the active speaker and add the word to their sentence
    # As soon as the speaker changes, finish their statement
    done = False
    init_active_speaker = -1
    active_speaker = init_active_speaker
    current_statement = ''
    transcript = []
    while not done:
        lowest_time = float('inf')
        for i, index in enumerate(speaker_index):
            if done_speakers[i] is True:
                continue
            if float(speaker_data[i]['data'][index]['starttime']) < lowest_time:
                new_active_speaker = i
                lowest_time = float(speaker_data[i]['data'][index]['starttime'])
        #pdb.set_trace()
        # add to transcript and reset current statement if the speaker changed

        if new_active_speaker is not active_speaker and active_speaker is not init_active_speaker:
            transcript.append({'speaker': speaker_data[active_speaker]['name'], 'statement': current_statement})
            current_statement = ''
        active_speaker = new_active_speaker
        # TODO: do something to point to the timestamps in the transcript
        current_statement += (speaker_data[active_speaker]['data'][speaker_index[active_speaker]]['text'])
        current_statement += ' '
        #speaker_index[active_speaker] += 1

        if speaker_index[active_speaker] == len(speaker_data[active_speaker]['data']) - 1:
            done_speakers[active_speaker] = True
        else:
            speaker_index[active_speaker] += 1

        # check if you're done
        done = all(done_speakers)

    return transcript


def aggregate_words(speaker_data):
    """
    Compiles a transcript from a bunch of different speakers
    :param speaker_data: a list of speaker structures - dicts w/ fields 'id', 'starttime', 'endtime', 'text': 
    :return: 
    """
    if len(speaker_data) is 0:
        return []
    # Keep track of index for each speaker data
    speaker_index = [0] * len(speaker_data)
    done_speakers = [False] * len(speaker_data)
    # Check to see if each speaker is talking
    # Set that person as the active speaker and add the word to their sentence
    # As soon as the speaker changes, finish their statement
    done = False
    transcript = []
    while not done:
        lowest_time = float('inf')
        for i, index in enumerate(speaker_index):
            if done_speakers[i] is True:
                continue
            if float(speaker_data[i][index]['starttime']) < lowest_time:
                new_active_speaker = i
                lowest_time = float(speaker_data[i][index]['starttime'])
        # add to transcript and reset current statement if the speaker changed
        active_speaker = new_active_speaker
        # TODO: do something to point to the timestamps in the transcript
        word = speaker_data[active_speaker][speaker_index[active_speaker]]
        word['speaker'] = active_speaker
        transcript.append(word)
        if speaker_index[active_speaker] == len(speaker_data[active_speaker]) - 1:
            done_speakers[active_speaker] = True
        else:
            speaker_index[active_speaker] += 1

        # check if you're done
        done = all(done_speakers)
    return transcript

def word_list_to_string(word_list, add_speaker=False):
    """
    Takes a list of words and 
    :param transcript: 
    :return: 
    """
    transcript = ""
    current_speaker = -1
    for word in word_list:
        if 'speaker' in word:
            if word['speaker'] is not current_speaker and add_speaker:
                transcript += "\n"
                transcript += "Speaker_%d: " % word['speaker']
                current_speaker = word['speaker']
        transcript += "%s "%word['text']
    return transcript


# Proposed way transcripts should be represented:
# List of words
def load_words(path):
    with open(path, 'r') as f:
        xml = f.read()
    words = xmltodict.parse(xml)['nite:root']['w']
    for word in words:
        word['text'] = word['#text']
        word['starttime'] = word['@starttime']
        word['endtime'] = word['@endtime']
    return words


def test_transcript_creation():
    dataset = 'ES2016a.A'
    xml_path = "%s/words/%s.words.xml" % (DATA_DIR, dataset)
    print("xml_path is %s" % xml_path)
    speakers = [{'name': 'speaker_1', 'dataset': 'ES2016a.A'},
                {'name': 'speaker 2', 'dataset': 'ES2016a.B'},
                {'name': 'speaker 3', 'dataset': 'ES2016a.C'},
                {'name': 'speaker 4', 'dataset': 'ES2016a.D'}]

    MAX_WORDS = 20
    for speaker in speakers:
        speaker['path'] = "%s/words/%s.words.xml" % (DATA_DIR, speaker['dataset'])
        with open(speaker['path'], 'r') as f:
            xml = f.read()
            speaker['data'] = xmltodict.parse(xml)['nite:root']['w']
            speaker['data'] = speaker['data'][0:MAX_WORDS]
    print(len(speakers))
    print([0] * len(speakers))

    transcript = compile_transcript(speakers)
    print(transcript)


def test_html_creation():
    dataset = 'ES2016a'
    audio_files = []
    target_dir = 'html_test'
    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    os.chdir(target_dir)
    for i in range(0,4):
        audio_name = "ES2016a.Headset-%d.wav"%i
        audio_file = '%s/%s/audio/%s'%(DATA_DIR, dataset, audio_name)
        audio_files.append(audio_name)
        copyfile(audio_file, audio_name)
    print ("audio files")
    print (audio_files)
    test_words = [{'text': 'Track0', 'starttime': 10.0, 'speaker': 0},
                  {'text': 'Track1', 'starttime': 10.0, 'speaker': 1},
                  {'text': 'Track2', 'starttime': 10.0, 'speaker': 2},
                  {'text': 'Track3', 'starttime': 10.0, 'speaker': 3}]
    create_audio_html('test.html', audio_files, test_words)



def test_full_stack():
    dataset = 'ES2016a'
    audio_files = []
    speaker_data = []
    appendices = ['A', 'B', 'C', 'D']
    target_dir = SERVER_TEMPLATE_DIR
    if not os.path.isdir(target_dir):
        os.mkdir(target_dir)
    #copyfile('mindstone_ui.js', '%s/mindstone_ui.js'%SERVER_STATIC_DIR)
    os.chdir(target_dir)
    for i in range(0, len(appendices)):
        audio_name = "ES2016a.Headset-%d.wav"%i
        audio_file = '%s/%s/audio/%s'%(DATA_DIR, dataset, audio_name)
        copyfile(audio_file, audio_name)
        audio_files.append(audio_name)
        xml_path = "%s/words/%s.%s.words.xml" % (DATA_DIR, dataset, appendices[i])
        speaker_data.append(load_words(xml_path))

    all_audio = {'master':'%s.Mix-Headset.wav'%(dataset)}
    words = aggregate_words(speaker_data)
    #print(word_list_to_string(words))
    create_audio_html('no_audio_test.html', {}, words)


if __name__=='__main__':
    print("woooooooo")
