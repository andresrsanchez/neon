## Page server architecture

The Page Server has a few different duties:

- Respond to GetPage@LSN requests from the Compute Nodes
- Receive WAL from WAL safekeeper
- Replay WAL that's applicable to the chunks that the Page Server maintains
- Backup to S3

S3 is the main fault-tolerant storage of all data, as there are no Page Server
replicas. We use a separate fault-tolerant WAL service to reduce latency. It
keeps track of WAL records which are not syncted to S3 yet.

The Page Server consists of multiple threads that operate on a shared
repository of page versions:

                                           | WAL
                                           V
                                   +--------------+
                                   |              |
                                   | WAL receiver |
                                   |              |
                                   +--------------+
                                                                                 +----+
                  +---------+                              ..........            |    |
                  |         |                              .        .            |    |
 GetPage@LSN      |         |                              . backup .  ------->  | S3 |
------------->    |  Page   |         repository           .        .            |    |
                  | Service |                              ..........            |    |
   page           |         |                                                    +----+
<-------------    |         |
                  +---------+      +--------------------+
		                   |   Checkpointing /  |
				   | Garbage collection |
                                   +--------------------+

Legend:

+--+
|  |   A thread or multi-threaded service
+--+

....
.  .   Component at its early development phase.
....

--->   Data flow
<---


Page Service
------------

The Page Service listens for GetPage@LSN requests from the Compute Nodes,
and responds with pages from the repository.


WAL Receiver
------------

The WAL receiver connects to the external WAL safekeeping service (or
directly to the primary) using PostgreSQL physical streaming
replication, and continuously receives WAL. It decodes the WAL records,
and stores them to the repository.


Repository
----------

The repository stores all the page versions, or WAL records needed to
reconstruct them. Each tenant has a separate Repository, which is
stored in the .zenith/tenants/<tenantid> directory.

Repository is an abstract trait, defined in `repository.rs`. It is
implemented by the LayeredRepository object in
`layered_repository.rs`. There is only that one implementation of the
Repository trait, but it's still a useful abstraction that keeps the
interface for the low-level storage functionality clean. The layered
storage format is described in layered_repository/README.md.

Each repository consists of multiple Timelines. Timeline is a
workhorse that accepts page changes from the WAL, and serves
get_page_at_lsn() and get_rel_size() requests. Note: this has nothing
to do with PostgreSQL WAL timeline. The term "timeline" is mostly
interchangeable with "branch", there is a one-to-one mapping from
branch to timeline. A timeline has a unique ID within the tenant,
represented as 16-byte hex string that never changes, whereas a
branch is a user-given name for a timeline.

Each repository also has a WAL redo manager associated with it, see
`walredo.rs`. The WAL redo manager is used to replay PostgreSQL WAL
records, whenever we need to reconstruct a page version from WAL to
satisfy a GetPage@LSN request, or to avoid accumulating too much WAL
for a page. The WAL redo manager uses a Postgres process running in
special zenith wal-redo mode to do the actual WAL redo, and
communicates with the process using a pipe.


Checkpointing / Garbage Collection
----------------------------------

Periodically, the checkpointer thread wakes up and performs housekeeping
duties on the repository. It has two duties:

### Checkpointing

Flush WAL that has accumulated in memory to disk, so that the old WAL
can be truncated away in the WAL safekeepers. Also, to free up memory
for receiving new WAL. This process is called "checkpointing". It's
similar to checkpointing in PostgreSQL or other DBMSs, but in the page
server, checkpointing happens on a per-segment basis.

### Garbage collection

Remove old on-disk layer files that are no longer needed according to the
PITR retention policy


### Backup service

The backup service, responsible for storing pageserver recovery data externally.

Currently, pageserver stores its files in a filesystem directory it's pointed to.
That working directory could be rather ephemeral for such cases as "a pageserver pod running in k8s with no persistent volumes attached".
Therefore, the server interacts with external, more reliable storage to back up and restore its state.

The code for storage support is extensible and can support arbitrary ones as long as they implement a certain Rust trait.
There are the following implementations present:
* local filesystem — to use in tests mainly
* AWS S3           - to use in production

Implementation details are covered in the [storage readme](./src/relish_storage/README.md) and corresponding Rust file docs.

The backup service is disabled by default and can be enabled to interact with a single remote storage.

CLI examples:
* Local FS: `${PAGESERVER_BIN} --relish-storage-local-path="/some/local/path/"`
* AWS S3  : `${PAGESERVER_BIN} --relish-storage-s3-bucket="some-sample-bucket" --relish-storage-region="eu-north-1" --relish-storage-access-key="SOMEKEYAAAAASADSAH*#" --relish-storage-secret-access-key="SOMEsEcReTsd292v"`

For Amazon AWS S3, a key id and secret access key could be located in `~/.aws/credentials` if awscli was ever configured to work with the desired bucket, on the AWS Settings page for a certain user. Also note, that the bucket names does not contain any protocols when used on AWS.
For local S3 installations, refer to the their documentation for name format and credentials.

Similar to other pageserver settings, toml config file can be used to configure either of the storages as backup backup targets.
Required sections are:

```toml
[relish_storage]
local_path = '/Users/someonetoignore/Downloads/tmp_dir/'
```

or

```toml
[relish_storage]
bucket_name = 'some-sample-bucket'
bucket_region = 'eu-north-1'
access_key_id = 'SOMEKEYAAAAASADSAH*#'
secret_access_key = 'SOMEsEcReTsd292v'
```

Also, `AWS_SECRET_ACCESS_KEY` and `AWS_ACCESS_KEY_ID` variables can be used to specify the credentials instead of any of the ways above.

TODO: Sharding
--------------------

We should be able to run multiple Page Servers that handle sharded data.