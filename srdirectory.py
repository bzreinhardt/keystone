import speech_credentials as sc
import speech_recognition as sr
import os
import pydub
import pdb
import time
import numpy as np

import json
from json2html import *
   
INPUT_DIR = "/Users/kon/Dropbox/sr-input"
OUTPUT_DIR = "/Users/kon/Dropbox/sr-output"
RESULT_CSV_FILE = "/Users/kon/Dropbox/sr-output/results.csv"

CONFIDENCE = "word_confidence"

fileID = "XXXX1TBD"
#
# TODO: aif file does not work
# make the output filename for JSON based on the input file name
# make this a function that can be called
# scan a folder and automatically 
# do the recognition in parallel
#

def Add_Confidence_To_Text_File(fileID, confidence):
    with open(RESULT_CSV_FILE, "a") as myfile:
        myfile.write( str(fileID)+","+str(confidence)+"\n")    

def create_HTML_FOLDER( input_file, output_directory ):
    audio_file = input_file
    sound = pydub.AudioSegment.from_mp3(audio_file)

    # Create a directory based on the file name that will hold all the results

    rawName_plus_path = os.path.splitext(audio_file)[0]
    baseFile = os.path.basename(rawName_plus_path)
    myDir = os.path.join(output_directory, baseFile)

    print "Output Directory: " + output_directory
    print "New Directory: " + myDir
    print "Full filename without extension: " + rawName_plus_path
    print "Base filename: " + baseFile
    
    try:
        a, b,fileID,d,e = baseFile.split("_")
        
    except:
        fileID = baseFile

    
    if not os.path.exists(myDir):
        os.makedirs(myDir)
    
    os.chdir(myDir)
    
    waveFile = baseFile + ".wav"
    sound.export(waveFile, format="wav")
    print "export done"
    wav_file = os.path.join(myDir, waveFile)

    print "wav_file is: " + wav_file

    AUDIO_CONTROL = '<audio id="audio2" \
       preload="auto" \
       src="'+ waveFile + '" > \
       \
       <p>Your browser does not support the audio element</p> \
    </audio> \
    \
    <script>\
      myAudio=document.getElementById("audio2");\
      myAudio.addEventListener("canplaythrough", function() {\
        this.play();\
      });\
      function setTime(curTime){myAudio.currentTime = curTime; } \
    </script>'



    #import pdb;pdb.set_trace()

    doIBM = 1
    doGoogle = 0
    doBing = 0


    r = sr.Recognizer()

    with sr.WavFile(wav_file) as source:
        print("Source duration: " + str(source.DURATION) )

        numAudioChunks = int(source.DURATION / 10) + 1
        numAudioChunks = 1
        chunkDuration = source.DURATION / numAudioChunks

        if doIBM == 1:
            print("======IBM=======")
            
            #if the target output file already exists, skip recognition and go straight to HTML output!
            #we're already in the correct directory, myDir
            if os.path.isfile('outputIBM.json'):
                outputIBMFile = open('outputIBM.json', 'r')
                srResult = json.load(outputIBMFile)
            else:
                outputIBMFile = open('outputIBM.json', 'w')

                for offset in range(numAudioChunks):
                    print("First offset is: " + str(offset))
                    audio = r.record(source, duration=chunkDuration)
                    try:
                        srResult = r.recognize_ibm(audio, username=sc.IBM_USERNAME, password=sc.IBM_PASSWORD, language = "en-US", show_all = True )
                        print("IBM Speech to Text thinks you said: \n " + str(srResult))
                        json.dump(srResult, outputIBMFile)

                        #write JSON to IBM HTML file
            
                        print "IBM Results: " + json.dumps(srResult)
                        
                    except sr.UnknownValueError:
                        print("Could not understand audio")
                        print("IBM Speech to Text could not understand audio")
            
                        wav_data = audio.get_wav_data(convert_rate = 16000, convert_width = 2)
                        print(offset)
                        with open("segment.wav", "wb") as f: f.write(wav_data)
                        break
                    except sr.RequestError as e:
                        print("Could not request results from IBM Speech to Text service; {0}".format(e))            
                
            with open("IBMhtmlOutput.html", "wb") as f: 
                f.write("<head> <title>" + baseFile + "</title> <style> .alt0 { color: black; } .alt1 { color: red; } </style> </head><body>")
                f.write("<h1>IBM JSON</h1><br>")
                f.write("<h2>Audio File: " + baseFile + "</h2><br>")
                f.write(AUDIO_CONTROL)
            
                #f.write(srResult["results"][0]["alternatives"][0]["transcript"])
                f.write("<br><h2>Clickable Transcript:</h2><br>")
                iii = 0
                alt_word_confidence_array = np.zeros(0)
                for results in srResult["results"]:
                    iii = iii+1
                    jjj = 0
                    for alternatives in results["alternatives"]:
                        npvar = np.array(alternatives[CONFIDENCE])
                        #import pdb;pdb.set_trace()
                        
                        word_confidence_array = npvar[:,1].astype(np.float)
                        print "Average of confidence array %s"%(np.mean(word_confidence_array))
                        alt_word_confidence_array = np.append(alt_word_confidence_array, np.mean(word_confidence_array))
                        jjj=jjj+1
                        kkk = 0
                        for words in alternatives["timestamps"]:
                            print "Word iii, jjj: " + str(iii) + ", " + str(jjj) + " " + words[0] + "start: "+ str(words[1]) + "end: "+ str(words[2])
                            print "Confidence: " + str(alternatives[CONFIDENCE][kkk][1])
                            confidence = alternatives[CONFIDENCE][kkk][1]
                            #only put the first alternative at the top
                            kkk = kkk+1
                            if jjj == 1:
                                f.write( '<a onClick="setTime(' + str(words[1]) + ');" style="cursor: pointer; cursor: hand; background-color: #FF'+format(int(confidence*255), 'x')+ format(int(confidence*255), 'x')+'"> ' +words[0]+' </a>')

                print "Average confidence across the file: %s"%(np.mean(alt_word_confidence_array))
                f.write("<br><h1>Confidence: " + str(np.mean(alt_word_confidence_array)) + "</h1><br>")
                Add_Confidence_To_Text_File(fileID, np.mean(alt_word_confidence_array))
                
                f.write("<br><h2>Transcript:</h2><br>")
            
                iii = 0
                for results in srResult["results"]:
                    iii = iii+1
                    jjj = 0
                    for alternatives in results["alternatives"]:
                        jjj=jjj+1
                        print "Transcript iii, jjj: " + str(iii) + ", " + str(jjj) + " " + alternatives["transcript"]
                        #only put the first alternative at the top
                        if jjj == 1:
                            f.write( '<span class="alt0">' + alternatives["transcript"] + "</span><br>")
                        if jjj == 2:
                            f.write( 'ALTERNATIVE: <span class="alt1">' + alternatives["transcript"] + "</span><br>")

                #Write the piece the skips in the audio player
                f.write("<br><h2>Raw JSON</h2>")
                f.write(json2html.convert(json = srResult, table_attributes="class=\"table table-bordered table-hover\""))
                f.write("</body>")
        
                #print(offset, ":", r.recognize_sphinx(audio))

        if doBing == 1:
            print("======BING=======")
            outputBingFile = open('outputBing.json', 'wb')
            # recognize speech using Microsoft Bing Voice Recognition
            try:
                srResult = r.recognize_bing(audio, key=sc.BING_KEY, language = "en-US", show_all = True)
                print("Microsoft Bing Voice Recognition thinks you said \n " + srResult)
                json.dump(srResult, outputBingFile)
            except sr.UnknownValueError:
                print("Microsoft Bing Voice Recognition could not understand audio")
            except sr.RequestError as e:
                print("Could not request results from Microsoft Bing Voice Recognition service; {0}".format(e))


        if doGoogle == 1:
            outputGoogleFile = open('outputGoogle.json', 'wb')
            print("======GOOGLE=======")
            GOOGLE_MAX_AUDIOSIZE = 15
            numAudioChunks = int(source.DURATION / GOOGLE_MAX_AUDIOSIZE) + 1
            chunkDuration = source.DURATION / numAudioChunks

            with open("GooglehtmlOutput.html", "wb") as f: 
                for offset in range(numAudioChunks):
                    print("First offset is: " + str(offset))
                    audio = r.record(source, duration=chunkDuration)

                    try:
                        # for testing purposes, we're just using the default API key
                        # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
                        # instead of `r.recognize_google(audio)`
                        #srResult = r.recognize_google(audio, key=GOOGLE_API_KEY, language = "en-US", show_all = True)
                        srResult = r.recognize_google(audio, language = "en-US", show_all = True)
                        print("Google Speech Recognition thinks you said: \n " + str(srResult))
                        json.dump(srResult, outputGoogleFile)
                    
                        f.write("<h1>Google JSON</h1><br>")
                        f.write("<h2>Audio File: " + baseFile + "</h2><br>")
                        f.write( json2html.convert(json = srResult, table_attributes="class=\"table table-bordered table-hover\"") )
                    except sr.UnknownValueError:
                        print("Google Speech Recognition could not understand audio")
                    except sr.RequestError as e:
                        print("Could not request results from Google Speech Recognition service; {0}".format(e))

#######
# The fun starts here!
#######
text = 0
while 1:
    for filename in os.listdir(INPUT_DIR):
        if filename.endswith(".mp3"): #or filename.endswith(".py"): 
            # print(os.path.join(directory, filename))
            create_HTML_FOLDER(os.path.join(INPUT_DIR, filename), OUTPUT_DIR )
            os.remove(os.path.join(INPUT_DIR, filename))
            text = 0
            continue
        else:
            continue
    if text == 0:
        print("Waiting for .mp3 file in ") + INPUT_DIR
        print("Press ctrl-c to exit ") + INPUT_DIR
        text = 1
    time.sleep (10)

