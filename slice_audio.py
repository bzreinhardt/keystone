import keystone
import argparse

if __name__=="__main__":
    parser = argparse.ArgumentParser("slice a file")
    parser.add_argument("file")
    parser.add_argument("sample_length", type=int)
    args = parser.parse_args()

    keystone.slice_audio_file(args.file, args.sample_length, export=True)
