Heavy Profile
=============

The project is built in three parts:

- **Profile generation** a script to create a Firefox "heavy" profile
- **Archive generation** a script to create a collection of zip files
- **Client Syncing** a script that synchronizes a local version of the profile

Profile generation
------------------

The tool maintains a local profile using Geckodriver.

XXX details


Archive generation
------------------

Once the local profile has been created, the tool
generates a ZIP files that can be downloaded by clients.

The directory structure is:

- profile: root of the profile
- archives: root of the zip files

The archives directory contains the last 10 versions of the
heavy profile, named with this pattern:

- YYYY-MM-DD-hp.zip
- latest.zip

Where latest.zip is a symbolic link to the latest version.

In order to speed up downloads, the tool also produces
zipped diffs so the client can update its local version without
having to download the whole zip everytime.

Diff files are using this naming pattern:

- diff-YYYY-MM-DD-YYYY-MM-DD-hp.zip

Where the first date is the oldest version.

The archives directory is published as a browsable HTTP directory.


Client Syncing
--------------

The client uses HTTP to get the index of files and the files.

On first run, the client downloads the latest archive and
decompresses the profile.

On the next runs, the client will try to download diffs to
update its local profile.

In case there's a patching issue, the profile is recreated
from scratch using the latest full archive.

