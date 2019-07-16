import platform
import os
import sys
import argparse
import asyncio
import json
import datetime

from arsenic import get_session
from arsenic.browsers import Firefox
from arsenic.services import Geckodriver, free_port, subprocess_based_service

from condprof.util import fresh_profile, latest_nightly
from condprof import logger
from condprof.scenario import scenario
from condprof.client import get_profile
from condprof.archiver import Archiver


class CustomGeckodriver(Geckodriver):
    async def start(self):
        port = free_port()
        await self._check_version()
        return await subprocess_based_service(
            [self.binary, "--port", str(port), "--marionette-port", "50499"],
            f"http://localhost:{port}",
            self.log_file,
        )


def get_age(metadata):
    created = metadata["created"][:26]
    updated = metadata["updated"][:26]
    # tz..
    format = "%Y-%m-%d %H:%M:%S.%f"
    created = datetime.datetime.strptime(created, format)
    updated = datetime.datetime.strptime(updated, format)
    delta = created - updated
    return delta.days


async def build_profile(args):
    scenarii = scenario[args.scenarii]

    if not args.force_new:
        get_profile(args)
    logger.msg("Updating profile located at %r" % args.profile)
    metadata_file = os.path.join(args.profile, ".hp.json")

    with open(metadata_file) as f:
        metadata = json.loads(f.read())

    f_args = ["-profile", args.profile]
    if platform.system() != "Darwin":
        f_args.append("-headless")

    caps = {"moz:firefoxOptions": {"args": f_args}}
    if args.firefox is not None:
        caps["moz:firefoxOptions"]["binary"] = args.firefox

    logger.msg("Starting the Fox...")
    with open("gecko.log", "a+") as glog:
        async with get_session(
            CustomGeckodriver(log_file=glog), Firefox(**caps)
        ) as session:
            logger.msg("Running the %s scenario" % args.scenarii)
            metadata.update(await scenarii(session, args))

    # writing metadata
    logger.msg("Creating metadata...")
    ts = str(datetime.datetime.now())
    if "created" not in metadata:
        metadata["created"] = ts
    metadata["updated"] = ts
    metadata["name"] = args.scenarii
    metadata["platform"] = sys.platform
    metadata["age"] = get_age(metadata)
    metadata["version"] = "69.0a1"  # add the build id XXX
    metadata["customization"] = "vanilla"  # add themes

    with open(metadata_file, "w") as f:
        f.write(json.dumps(metadata))

    logger.msg("Profile at %s" % args.profile)
    logger.msg("Done.")


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description="Profile Creator")
    parser.add_argument("profile", help="Profile Dir", type=str)
    parser.add_argument("archive", help="Archives Dir", type=str, default=None)

    parser.add_argument(
        "--max-urls", help="How many URLS to visit", type=int, default=115
    )
    parser.add_argument("--firefox", help="Firefox Binary", type=str, default=None)
    parser.add_argument("--scenarii", help="Scenarii to use", type=str, default="heavy")
    parser.add_argument(
        "--archives-server",
        help="Archives server",
        type=str,
        default="http://condprof.dev.mozaws.net",
    )
    parser.add_argument(
        "--fresh-profile",
        help="Create a fresh profile",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--archives-dir", help="Archives local dir", type=str, default="/tmp/archives"
    )
    parser.add_argument(
        "--force-new", help="Create from scratch", action="store_true", default=False
    )
    args = parser.parse_args(args=args)
    if not os.path.exists(args.profile):
        fresh_profile(args.profile)

    loop = asyncio.get_event_loop()
    with latest_nightly(args.firefox) as binary:
        args.firefox = os.path.abspath(binary)
        try:
            loop.run_until_complete(build_profile(args))
        finally:
            loop.close()

    if not args.archive:
        return

    logger.msg("Creating archive")
    archiver = Archiver(args.profile, args.archive, no_signing=True)
    age = archiver.metadata["age"]
    if age < 7:
        age = "days"
    elif age < 30:
        age = "weeks"
    elif age < 30 * 6:
        age = "months"
    else:
        age = "old"  # :)

    archiver.metadata["age"] = age
    # the archive name is of the form
    # profile-<platform>-<type>-<age>-<version>-<customization>.tgz
    name = "profile-%(platform)s-%(name)s-%(age)s-" "%(version)s-%(customization)s.tgz"
    name = name % archiver.metadata
    archive_name = os.path.join(args.archives_dir, name)
    # no diffs for now
    archiver.create_archive(archive_name)
    logger.msg("Archive created at %s" % archive_name)


if __name__ == "__main__":
    main()
