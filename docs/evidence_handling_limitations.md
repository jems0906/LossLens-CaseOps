# Evidence Handling and Limitations

The register stores a source reference, collector role, collection time, event time, optional SHA-256 file hash, and notes. Evidence register access and metadata changes are recorded with a synthetic actor identifier and timestamp in the SQLite audit table. The demo has one shared token per role, so this is not individual identity attribution.

A hash can help detect whether a file later differs from the hashed bytes. It does not prove who created the file, when the original was created, whether it is complete, whether the source is authentic, or whether it is admissible. It also does not prevent changes to the database or audit table.

The audit table is an application-level record, **not immutable**. This demo has no external append-only store, signed audit chain, trusted timestamping, retention lock, or independent audit replication. Do not describe it as tamper-proof or immutable.

All included examples use synthetic records. Do not enter real associate names, badge IDs, package IDs, customer addresses, incident details, or internal screenshots. Production use would require organization-approved identity, encryption, key management, authorization policy, retention controls, backups, audit monitoring, and legal/privacy review.