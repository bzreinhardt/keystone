import xmltodict
import os
from shutil import copyfile
import pdb

DATA_DIR = os.environ['DATA_DIR']
SERVER_STATIC_DIR = os.environ['KEYSTONE']+'/webapp/static'
SERVER_TEMPLATE_DIR = os.environ['KEYSTONE']+'/webapp/templates'

def create_header():
    text = """<head> <title>MobileAppCall</title> \n
    <head>\n
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n
    <link rel=\"stylesheet\" href=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css\">\n
    <script src=\"https://ajax.googleapis.com/ajax/libs/jquery/3.2.0/jquery.min.js\"></script>\n
    <script src=\"https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js\"></script>\n
    <style> .alt0 { color: black; } .alt1 { color: red; }\n
    <style>\n
    h1 {\n
    background-color: lightgrey;\n
    } </style>\n
    </head>\n
    <body style=\"margin:20;padding:0\">\n
    <div id="popover-content" class="hide"> \n
    <input type="text" name="email" id="email"/>\n
    </div>\n"""
    return text


def create_audio_element(filename, id="audio2"):
    text =  """<audio id="%s" preload=\"auto\" src = "%s"> \n
    <p> Your browser does not support the audio element </p>\n
    </audio>\n 
    """%(id, filename)
    return text


def create_js(all_audio):
    audio_ids = all_audio.keys()
    audio_id_string = ""
    for audio_id in audio_ids:
        audio_id_string += "audios['%s']=document.getElementById(\"%s\")\n"%(audio_id, audio_id)
    text = """
    <script>\n
    audios = {};\n
    %s
    for (var audio_id in audios) {\n
      audios[audio_id].addEventListener("canplaythrough", function() {this.play();});\n
    }\n
    \n
    function pauseAllAudio(){\n
      for (var audio_id in audios) {\n
      audios[audio_id].pause();\n
    }\n
    }\n
    function setTime(curTime, audio_id){\n
      pauseAllAudio();\n
      audios[audio_id].currentTime = curTime; \n
      audios[audio_id].play();\n
    }\n
    window.onload = function(){ pauseAllAudio() }\n
    </script>\n
    """%audio_id_string
    return text

def confidence_to_hex(confidence):
    return '#FF' + format(int(confidence * 255), 'x') + format(int(confidence * 255), 'x')

def word_to_html(word, master_audio=None):
    """
    converts a word to an html element
    :param word - dictionary with 'text': 
    :return html - line of html that will play the word in the recording: 
    """
    confidence = 1.0
    if 'confidence' in word:
        confidence = word['confidence']
    speaker = str(word['speaker'])
    if master_audio is not None:
        speaker = master_audio
    #pdb.set_trace()
    html = '<a rel="popover" id=word_' + word['nite:id']+ ' onClick="setTime(' + str(
            word['starttime']) + ', \'' +  speaker + '\');" style="cursor: pointer; cursor: hand; background-color: #FF' + format(
            int(confidence * 255), 'x') + format(int(confidence * 255), 'x') + '"> ' + word['text'] + ' </a>'
    return html

def audio_button_html():
    return "<h1> <button type=\"button\" onclick = \"pauseAllAudio();\" > Stop Audio </button> </h1> <br>"


def create_audio_html(filename, all_audio, words):
    """
    
    :param filename: 
    :param all_audio: dictionary with keys as audio track identifiers and value as the filename 
    :param words: 
    :return: 
    """
    with open(filename, 'w') as f:
        f.write("{% extends \"header.html\" %} {% block body %}")
        f.write('<body>')
        f.write('\n')
        for audio in all_audio:
            f.write(create_audio_element(all_audio[audio], audio))
        f.write('\n')
        f.write(create_js(all_audio))
        f.write('<br>')
        f.write('\n')
        f.write(audio_button_html())
        f.write('\n')
        f.write('<br>')
        f.write('\n')
        previous_speaker = -1
        for word in words:
            if previous_speaker is not word['speaker']:
                f.write('<br>\n')
                f.write('Speaker %d: '%word['speaker'])
            f.write(word_to_html(word, master_audio='master'))
            f.write(' ')
            previous_speaker = word['speaker']
        f.write('\n')
        f.write('{% endblock %}')


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

def word_list_to_string(word_list):
    """
    Takes a list of words and 
    :param transcript: 
    :return: 
    """
    transcript = ""
    current_speaker = -1
    for word in word_list:
        if word['speaker'] is not current_speaker:
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
    test_full_stack()
