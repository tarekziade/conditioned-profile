Heavy Profile
=============

The project is built in three parts:

- **Profile generation** a script to create a Firefox "heavy" profile
- **hp-archiver** a script to create a collection of zip files
- **Client Syncing** a script that synchronizes a local version of the profile

Profile generation
------------------

The tool maintains a local profile using Geckodriver.

XXX details


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
decompresses the profile after verifyng the checksum. It
also optionally checks the GPG signature.

On the next runs, the client will try to download diffs to
update its local profile.

In case there's a patching issue, the profile is recreated
from scratch using the latest full archive.

