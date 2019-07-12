# client for conditioned profiles
import os
import tarfile
import functools

from clint.textui import progress
from condprof import logger
from condprof.util import check_exists, download_file, TASK_CLUSTER


TC_LINK = (
    "https://index.taskcluster.net/v1/task/garbage.condprof/"
    "artifacts/public/today-%s.tgz"
)


def get_profile(args):

    # getting the latest archive from the server
    if TASK_CLUSTER:
        url = TC_LINK % args.scenarii
        basename = "today-%s.tgz" % args.scenarii
    else:
        basename = "%s-latest.tar.gz" % args.scenarii
        url = args.archives_server + "/%s" % basename
    exists, __ = check_exists(url)

    if not exists:
        return None

    target = os.path.join(args.archives_dir, basename)
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
                    pass

            tar.old = tar.extract
            tar.extract = functools.partial(_extract, tar)
            tar.extractall(args.profile)

    return args.profile
