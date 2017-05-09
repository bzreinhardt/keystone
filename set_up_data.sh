export DATA_DIR='amicorpus'
curl -o /tmp/ami_public_manual_1.6.2.zip 'http://groups.inf.ed.ac.uk/ami/AMICorpusAnnotations/ami_public_manual_1.6.2.zip'
unzip /tmp/ami_public_manual_1.6.2.zip -d $DATA_DIR

# Grab the audio
wget    -P $DATA_DIR/ES2016a/audio http://groups.inf.ed.ac.uk/ami/AMICorpusMirror//amicorpus/ES2016a/audio/ES2016a.Mix-Headset.wav
wget    -P $DATA_DIR/ES2016a/audio http://groups.inf.ed.ac.uk/ami/AMICorpusMirror//amicorpus/ES2016a/audio/ES2016a.Headset-0.wav
wget    -P $DATA_DIR/ES2016a/audio http://groups.inf.ed.ac.uk/ami/AMICorpusMirror//amicorpus/ES2016a/audio/ES2016a.Headset-1.wav
wget    -P $DATA_DIR/ES2016a/audio http://groups.inf.ed.ac.uk/ami/AMICorpusMirror//amicorpus/ES2016a/audio/ES2016a.Headset-2.wav
wget    -P $DATA_DIR/ES2016a/audio http://groups.inf.ed.ac.uk/ami/AMICorpusMirror//amicorpus/ES2016a/audio/ES2016a.Headset-3.wav

