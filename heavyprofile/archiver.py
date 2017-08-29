"""Maintains an archives directory given a profile
"""
import sys
import argparse
import tarfile
import os
import glob
from datetime import date


def _log(msg):
    print(msg)


def create_archives(profile_dir, archives_dir):
    today = date.today()
    archive = today.strftime('%Y-%m-%d-hp.tar.gz')
    _log("Creating %s..." % archive)
    archive = os.path.join(archives_dir, archive)

    with tarfile.open(archive, "w:gz") as tar:
        for filename in glob.glob(os.path.join(profile_dir, "*")):
            _log("\tAdding %s..." % filename)
            tar.add(filename, os.path.basename(filename))

    _log("Done.")


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Archiver')
    parser.add_argument('profile-dir', help='Profile Dir', type=str)
    parser.add_argument('archives-dir', help='Archives Dir', type=str)
    args = parser.parse_args(args=args)
    create_archives(args.profile_dir, args.archives_dir)


if __name__ == "__main__":
    main()
