#!usr/bin/env python
from google.cloud import storage
import argparse
from datetime import datetime

DB_BLOB = 'db.sqlite3'
DB_FILE = 'db.sqlite3'

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--squash_cloud', action='store_true')
    parser.add_argument('--squash_local', action='store_true')
    args = parser.parse_args()

    client = storage.Client()
    bucket = client.get_bucket('illiad-audio')
    blob = bucket.blob(DB_BLOB)

    if args.squash_cloud:
        with open(DB_FILE, 'rb') as f:
            blob.upload_from_file(f)

    if args.squash_local:
        with open(DB_FILE, 'wb') as f:
            blob.download_to_file(f)