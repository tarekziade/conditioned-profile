Heavy Profile
=============

The project is built in three parts:

- **hp-creator** a script to create a Firefox "heavy" profile
- **hp-archiver** a script to create a collection of tar-gzipped files
- **hp-sync** a script that synchronizes a local version of the profile

hg-creator
----------

The tool maintains a local profile using Arsenic & Geckodriver,
it visits random pages using a dictionary of words.

To run it, just point the profile directory::

    $ hp-creator /tmp/profile --max-urls 10
    Updating profile located at '/tmp/profile'
    Starting the Fox...
    1/10 https://www.ebay.com/sch/i.html?_from=R40&_trksid=p2380057.m570.l1313.TR0.TRC0.H0.Xbottle.TRS0&_nkw=unit
    2/10 https://www.amazon.com/s/ref=nb_sb_noss_2?url=search-alias%3Daps&field-keywords=child
    3/10 https://www.bing.com/search?q=create+list+of+nounsmover
    4/10 https://www.bing.com/search?q=create+list+of+nounsraccoon
    5/10 https://search.yahoo.com/yhs/search?p=cat
    6/10 https://www.youtube.com/results?search_query=fan
    7/10 https://www.google.com/search?q=humor
    8/10 https://www.bing.com/search?q=create+list+of+nounsscience
    9/10 https://www.youtube.com/results?search_query=creator
    10/10 https://www.ebay.com/sch/i.html?_from=R40&_trksid=p2380057.m570.l1313.TR0.TRC0.H0.Xbottle.TRS0&_nkw=sewer
    Done.

If the profile does not exists, it will generate a new one.

The profile also gets the latest Firefox Nightly and uses it
automatically.


hp-archiver
-----------

Once the local profile has been created, **hp-archiver** can
generate a ZIP file that can be downloaded by clients.

**hp-archiver** takes two arguments to run:

- the **profile** directory
- the **archives** directory

The **archives** directory is populated by the script with
tar-gzipped archives of the profiles. It contains up to ten
10 versions of the heavy profile, named with this pattern:

- YYYY-MM-DD-hp.tar.gz
- YYYY-MM-DD-hp.tar.gz.sha256 <== checksum
- latest.tar.gz

Where latest.tar.gz is a symbolic link to the latest version.

The archive contains an embedded GPG signature for verifying the
origin and authenticity of the profile if needed.

In order to speed up downloads, the tool also produces
tar-gzipped diffs so the client can update its local version without
having to download the whole archive everytime.

Diff files are using this naming pattern:

- diff-YYYY-MM-DD-YYYY-MM-DD-hp.tar.gz
- diff-YYYY-MM-DD-YYYY-MM-DD-hp.tar.gz.sha256

Where the first date is the oldest version.

The archives directory is published as a browsable HTTP directory.


Example::

    $ hp-archiver /tmp/profile /tmp/archives/
    Creating 2017-08-31-hp.tar.gz...
    => Adding /tmp/profile/addonStartup.json.lz4...
    ...
    => Adding /tmp/profile/xulstore.json...
    Done.
    Creating a diff tarball with the previous day
    => 6183 new files, 255 modified, 5 deleted.
    Done.



hp-sync
-------

The client uses HTTP to get the index of files and the files.

On first run, the client downloads the latest archive and
decompresses the profile after verifying the checksum. It
also optionally checks the GPG signature::

    $ hp-sync /tmp/profile2
    Syncing profile located at '/tmp/profile2'
    This is a new profile
    Full download...
    Downloading http://localhost:8000/2017-09-01-hp.tar.gz
    [################################] 295599/295599 - 00:00:15
    Extracting everything in '/tmp/profile2'
    [################################] 19302/19302 - 00:00:08
    Done.


On the next runs, the client will try to download diffs to
update its local profile::

    $ hp-sync /tmp/profile2
    Syncing profile located at '/tmp/profile2'
    Check if 'diff-2017-08-31-2017-09-01-hp.tar.gz' exists
    Backing up the profile...
    Diffs download...
    Downloading http://localhost:8000/diff-2017-08-31-2017-09-01-hp.tar.gz
    [################################] 1/1 - 00:00:00
    Applying diff 'diff-2017-08-31-2017-09-01-hp.tar.gz'...
    [################################] 0/0 - 00:00:00
    Done.

In case there's a patching issue, the profile is recreated
from scratch using the latest full archive.

