"""Maintains an archives directory given a profile
"""
import sys
import argparse


def create_archives(profile_dir, archives_dir):
    pass


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Archiver')
    parser.add_argument('profile-dir', help='Profile Dir', type=str)
    parser.add_argument('archives-dir', help='Archives Dir', type=str)
    args = parser.parse_args(args=args)
    create_archives(args.profile_dir, args.archives_dir)


if __name__ == "__main__":
    main()
