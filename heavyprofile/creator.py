import platform
import os
import sys
import argparse
import asyncio
import json
import functools
import tarfile

from arsenic import get_session
from arsenic.browsers import Firefox
from arsenic.services import Geckodriver, free_port, subprocess_based_service

from heavyprofile.util import fresh_profile, latest_nightly
from heavyprofile.util import check_exists, download_file, TASK_CLUSTER
from heavyprofile import logger
from heavyprofile.scenario import scenario

from clint.textui import progress



class CustomGeckodriver(Geckodriver):
    async def start(self):
        port = free_port()
        await self._check_version()
        return await subprocess_based_service(
            [self.binary, '--port', str(port), '--marionette-port', '50499'],
            f'http://localhost:{port}',
            self.log_file
        )


async def build_profile(args):
    scenarii = scenario[args.scenarii]

    # getting the latest archive from the server
    url = args.archives_server + '/%s-latest.tar.gz' % args.scenarii
    exists, headers = check_exists(url)
    metadata = {}

    if exists:
        target = os.path.join(args.archives_dir, '%s-latest.tar.gz' %
                              args.scenarii)
        archive = download_file(url, target=target, check_file=False)
        with tarfile.open(archive, "r:gz") as tar:
            logger.msg("Checking the tarball content...")
            size = len(list(tar))
            with progress.Bar(expected_size=size) as bar:
                def _extract(self, *args, **kw):
                    if not TASK_CLUSTER:
                        bar.show(bar.last_progress + 1)
                    try:
                        return self.old(*args, **kw)
                    finally:
                        if args[0].name == ".hp.json":
                            import pdb; pdb.set_trace()

                tar.old = tar.extract
                tar.extract = functools.partial(_extract, tar)
                tar.extractall(args.profile)

    logger.msg("Updating profile located at %r" % args.profile)

    f_args = ["-profile", args.profile]
    if platform.system() != 'Darwin':
        f_args.append('-headless')

    caps = {"moz:firefoxOptions": {"args": f_args}}
    if args.firefox is not None:
        caps['moz:firefoxOptions']['binary'] = args.firefox

    logger.msg("Starting the Fox...")
    with open('gecko.log', 'a+') as glog:
        async with get_session(CustomGeckodriver(log_file=glog),
                               Firefox(**caps)) as session:
            metadata = await scenarii(session, args)

    # writing metadata
    logger.msg("Creating metadata...")
    metadata['name'] = args.scenarii
    with open(os.path.join(args.profile, '.hp.json'), 'w') as f:
        f.write(json.dumps(metadata))

    logger.msg("Done.")


def main(args=sys.argv[1:]):
    parser = argparse.ArgumentParser(description='Profile Creator')
    parser.add_argument('profile', help='Profile Dir', type=str)
    parser.add_argument('--max-urls', help='How many URLS to visit',
                        type=int, default=115)
    parser.add_argument('--firefox', help='Firefox Binary',
                        type=str, default=None)
    parser.add_argument('--scenarii', help='Scenarii to use',
                        type=str, default='simple')
    parser.add_argument('--archives-server', help="Archives server",
                        type=str,
                        default='http://heavyprofile.dev.mozaws.net')
    parser.add_argument('--fresh-profile', help='Create a fresh profile',
                        action='store_true', default=False)
    parser.add_argument('--archives-dir', help="Archives local dir",
                        type=str,
                        default='/tmp/archives')

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


if __name__ == '__main__':
    main()
