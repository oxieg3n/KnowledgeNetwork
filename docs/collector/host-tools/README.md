# Owner-run installed-model inspector

Run `inspect_installed_voxcpm2.cmd` on BLACKHAT-BASE from the reviewed versioned host kit. It uses the existing canonical engine Python, imports package metadata and Hugging Face cache constants, and reads the exact cached `openbmb/VoxCPM2` `refs/main` snapshot selected by the existing CLI. It does not import Torch or VoxCPM, load a model, execute the narrator, download, or change original files.

This is a potentially heavy sequential read of all snapshot files (at most 256 entries); run it only when no model job or other heavy hash is active. It creates a fresh `private-inventory-<uuid>` folder beside the inspector and applies a protected owner/SYSTEM/Administrators DACL **only to that new folder**, then reuses the host spool ACL verifier before writing `inventory.json`. Existing directory ACLs are never changed. Keep the kit in an owner-controlled directory; this check does not audit ancestors or defend against local administrators.

Console output names only the relative report folder. The report contains private resolved cache/blob/package paths and must stay private, outside Git. A successful inventory is not model-license approval, voice consent, runtime GPU evidence, narration parity, or proof somebody listened. It records the currently selected cached revision; `refs/main` and the effective cache environment must remain bound to the reviewed manifest before any inference. No arbitrary input paths or arguments are accepted. Failures are redacted and do not produce a success report.

Failure diagnostics use fixed stage names and exception types, never raw exception messages. After the new folder's DACL has been verified, a private failure.json can record up to 16 stack file/line/function entries; it contains private paths and must not be committed. Before ACL verification no diagnostic file is written. An old generic BLOCKED result without a report cannot establish which stage failed.

Private failure context includes bounded Python executable/version, installed voxcpm metadata version when available, and effective HF_HUB_CACHE only if its constants module was already loaded. These fields never appear on the console; no environment dump or new inference import is performed.


The new private folder retains its existing owner; only its DACL is replaced. This avoids requiring WRITE_OWNER merely to restrict a folder already owned by the caller. Windows permits the owner to change its DACL; changing ownership requires separate rights ([Microsoft SetNamedSecurityInfoW](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setnamedsecurityinfow)). The final verifier still rejects untrusted owners, null/inherited DACLs and missing current-user FullControl. Owner permission to create/read/change the new folder DACL is required; failure blocks report writing. Non-elevated host execution has not been verified.

## Shared Hugging Face blobs

The catalog accepts regular repository-local files and a direct file symlink to
the canonical effective `HF_HUB_CACHE/blobs/<two lowercase hex>/<64 lowercase hex>`
store. The shard must equal the first two object-ID characters. A second link is
allowed only for the observed HF layout: snapshot file -> repository's
`blobs/<64 lowercase hex>` file -> canonical shared blob. No extra hop, arbitrary
repository alias, linked directory or external target is allowed. This root is derived from the same cache as the
verified model repository; callers cannot supply an extra allowed directory.
Windows extended drive names returned by readlink are normalized narrowly;
device/UNC targets, unexpected file-link chains, arbitrary external
files, malformed names, broken references and nonregular files remain denied.

Shared-store names use the Xet object ID in the installed Hugging Face source,
not necessarily the file's SHA-256. The inspector hashes the actual resolved
contents separately; it does not incorrectly assert that the Xet ID is a SHA-256.

The private manifest retains each snapshot logical path, resolved target, actual
SHA-256 and bytes. The same 256-entry/32GiB total limits apply, including duplicate
logical references. File/link identity, size, mtime and ctime are checked around
hashing; link targets are revalidated afterward. Unreadable subdirectories fail
the inventory rather than silently producing a partial success. Snapshot/ref
selection is unchanged and a changed revision still fails. No cache variables,
model files, narrator script/reference, packages or network settings are changed.
Rejected reparse components have bounded path/type/tag/link-target details in
the protected private failure report only. The console still exposes no paths or
raw exception messages. Inspection success alone does not verify rights or speech.
