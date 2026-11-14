# V9 host inspector repair and actual verification

The existing feature branch continues from protected checkpoint `e904f15`.
Inspector repair source commit: `f6b94d7`; subsequent small review change adds
explicit UNC denial before any target I/O and marks the Windows-only report
orchestration test as such for Linux CI. No Collector rebuild/install, model
move/download, narrator rewrite, host execution channel, environment change,
Universal Gateway or network change occurred. Publication remains PAUSED.

## Root cause and correction

Initial repository-only containment rejected real HF shared blobs. Owner-run
private diagnostics then established the exact installed layout:
`snapshot/file -> repository/blobs/<64-hex etag> -> HF_HUB_CACHE/blobs/<2-hex prefix>/<64-hex Xet ID>`.
The installed Hugging Face `utils/_shared_blobs.py` confirms this layout and
regular final targets; its source SHA-256 is
`00277be9150b5c4268a7675f6f5ae8bf277cb50174f68a0c23a72764dba4055f`.
Xet IDs differ from file SHA-256. The inspector validates the shard/name shape,
then separately hashes actual resolved contents. It does not confuse cache IDs
with content SHA-256. The first repair was too strict about direct links only;
the owner-run failures and all source revisions are preserved privately.

Only regular repository-local files, direct canonical shared-blob links, and
that exact bounded two-hop HF chain are accepted. Intermediate identity/link
text and final file identity/size/mtime/ctime are checked before/after hashing.
Broken references, arbitrary external paths, malformed shard/hash names, UNC/
device aliases, linked directories/junctions, other chains and extra hops fail
closed. Windows readlink's extended drive prefix is normalized narrowly.
Unreadable traversal also fails instead of silently yielding partial inventory.
The 256-entry and32GiB total limits and exact ref/snapshot selection remain.
Private manifests retain logical path, resolved target, actual SHA-256 and bytes.

## Actual host result: PASS inventory only

Owner ran the existing entry point on BLACKHAT-BASE with Python3.11.16/VoxCPM2.0.3.
Verified selected revision: `7936080b41163874f38610f46f438e2c0757f9fd`.
Nine model/snapshot files:4,960,731,830 bytes;39 package files inventoried.
Inventory SHA-256:
`8db573cd5c002dd3e934f6b03dfbb6a78ad4245d263070a320a6db1914a08898`.

| Snapshot file | Actual bytes | Actual content SHA-256 |
| --- | ---: | --- |
| audiovae.pth |376951122|`94b5d51e107e0507d4acc976cfdadb64edd6fd06d1f751dadbf2fd1594274bf1`|
| model.safetensors |4580080592|`f7f964cfa9da23653baec6e6f7750719977ad944ed9f95fe52fe3a620506891d`|

Host private report:
`D:/projects/knowledgenetwork/collector-narrator-v9-004/docs/collector/host-tools/private-inventory-0fc6b750b895482c9421c2b5ae969066/inventory.json`.
Protected FORGE copy and rights evidence:
`C:/admin/collector-v9/inspector-provenance`.
No model load, inference, download or actual WAV generation was performed.

## Kit, tests and preservation

Existing local and redirected host kit004 updated; all original public kit files
were verified against their old manifest before copying into
`previous-revisions/inspector-e904f15-before-sharedblob-fix`. Intermediate failed/
diagnostic revisions and the successful host version are also retained there.
New private reports were not overwritten or included in public ZIPs.

Same exact owner-run command to repeat inspection:

```powershell
& 'D:\projects\knowledgenetwork\collector-narrator-v9-004\Inspect-InstalledVoxCPM.cmd'
```

Latest repair ZIP:
`C:/Admin/Projects/KnowledgeNetwork/output/The-Knowledge-Network-Collector-Narrator-V9-004-sharedblob-repair-final.zip`
SHA-256 `5a352c16550925171028c68b6257435868209c77db1ca6a688c69a30b0906a7f`.
Latest inspector SHA-256 `9790fe3fb76c86d73eed6c382420fecabf9fd2b26ef52e4cd72bbc4641d68f25`.
The actual successful host run used inspector SHA-256
`7e4625b8218cfd91cace9ef997ab9dbb2e4b7e94e92ac22d867a2982bb10f2e6`;
latest code differs only by the stricter explicit UNC guard. That last guard
passed the24 actual Windows focused tests; its host rerun is not claimed.

PASS:24 inspector Windows tests, including real absolute/relative symlinks,
canonical2-hop layout, escaped/malformed/broken/chained targets, content/link
replacement during hashing, size/count limits, exact revision/change detection,
private diagnostic redaction and unreadable traversal. PASS:23 narrator host/
contract regression tests (MOCK inference only). Logs/receipts are under
`C:/admin/collector-v9`. Python3.11 syntax checked. Ponytail FULL connected-code
review plus independent security review found no remaining concrete issue.
No expensive Collector rebuild or full-media regression was repeated.

Canonical narrator script/reference/CLI SHA-256 still match prior verified
`98b75e...f189`, `050db3...fe44`, `582115...7492` respectively (full digests in
HANDOFF). Installer/managed worker/operations.json digests remain unchanged.
Both original protected backups retain their original Git bundle hashes;
existing worktrees and checkpoint history remain intact.

## Rights/provenance after inventory: remaining actual blockers

The cached README digest exactly matches the upstream model card at the verified
revision: `feb850b390aa5051b81cbdc73b048361273552f003dd386b4da9c39ec9b6f055`.
That [revision's model card](https://huggingface.co/openbmb/VoxCPM2/blob/7936080b41163874f38610f46f438e2c0757f9fd/README.md)
declares Apache-2.0/commercial use. The snapshot has no separate LICENSE file;
its upstream LICENSE URL returned404. Installed package LICENSE was read and
hash-matched to the inventory:
`4f10acc209addacfad28293315c74c4cd648f771ee1263a748f1781d1e0265e4`.
No model download or license acceptance was performed. These are source/license
facts, not an assertion that all legal review is finished.

Still BLOCKED/NOT TESTED separately:
- Exact reference voice consent/commercial-use evidence is not supplied; remaining
  component/dependency obligations are not fully reviewed. No valid reviewed
  runtime manifest or fabricated approval booleans were generated.
- Unchanged-script smoke, independent runtime parity/GPU execution and new WAV
  have not been observed. Host-only success would still not prove remote speech.
- Dedicated authenticated host service, HTTPS route and scoped bearer are not
  deployed/configured. Gateway and old VoiceStudio route are untouched.
- Assistant's reported `untrusted_pipe_server` requires its actual client/token/
  executable context; developer health PASS does not prove Dot success.
- Exact intro badge and portrait/landscape outro bytes remain BLOCKED_ASSET;
  bounded metadata/backup review found no new location. Never substitute media.

Inventory PASS does not make remote narration operational or satisfy the full
45-55s branded/narrated Assistant acceptance test. Public publishing stays PAUSED.
