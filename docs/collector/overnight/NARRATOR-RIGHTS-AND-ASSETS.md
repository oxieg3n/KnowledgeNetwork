# Narrator rights and exact brand assets

November 14, 2026. Publication remains **PAUSED**. This read-only review continues
checkpoint `6a76f44`; it did not repeat the passed model inventory, execute host
Python or inference, accept licenses, modify the host, or substitute media.

## Reference consent: BLOCKED

The canonical Oxiegen-Narrator voice directory currently contains only
`narrate.ps1` and `reference.wav`. Existing protected rights evidence records
consent as not supplied. The reference SHA-256 remains
`050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44`.
Possession of this file and approval of narrator settings do not establish
permission to clone its speaker or commercially use the recording.

Retain a private signed/dated consent or applicable license identifying:

- The exact reference digest, speaker/source and recording provenance.
- Who owns or may authorize use of the recording and voice.
- Explicit permission for synthetic voice cloning and narration using this voice.
- Commercial/monetized YouTube use for Powered By Oxieg3n, with any restrictions,
  duration, territory, attribution or withdrawal terms.
- The authorizing party and review date. For a synthetic reference, preserve the
  source generator/model and its applicable output-use terms instead of inventing
  a human-speaker consent record.

Keep identities and supporting records private. No reviewed manifest booleans
were set by this review.

## Installed model and components: bounded evidence

The passed inventory at VoxCPM2 revision
`7936080b41163874f38610f46f438e2c0757f9fd` remains authoritative.
[The exact model card](https://huggingface.co/openbmb/VoxCPM2/blob/7936080b41163874f38610f46f438e2c0757f9fd/README.md)
declares Apache-2.0 and commercial use. Its saved digest is
`feb850b390aa5051b81cbdc73b048361273552f003dd386b4da9c39ec9b6f055`.
Installed VoxCPM 2.0.3 declares Apache-2.0; its LICENSE digest is
`4f10acc209addacfad28293315c74c4cd648f771ee1263a748f1781d1e0265e4`.
The earlier missing separate snapshot LICENSE remains documented, not repaired
by creating a substitute.

Under [Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0), redistribution
requires retaining the license and applicable notices, marking modified files,
and carrying relevant NOTICE attribution. It grants no general trademark rights.
These terms do not supply reference-voice consent.

Read-only installed metadata/license inspection additionally established:

| Installed component | Observed licensing evidence |
| --- | --- |
| torch 2.11.0+cu128 | BSD headline; full LICENSE also contains NVIDIA EULA/proprietary notices and bundled component terms |
| torchaudio 2.11.0+cu128 | BSD license retained in installed distribution |
| torchcodec 0.17.0 | BSD-3-Clause plus separate bundled third-party notices |
| soundfile 0.14.0 | BSD wrapper; bundled libsndfile has LGPL-2.1 COPYING |
| soxr 1.1.0 | Metadata declares LGPL-2.1-or-later |
| transformers 5.23.0, huggingface-hub 2.4.0 | Apache-2.0 metadata/licenses |
| tokenizers 0.23.3, wetext 0.2.1 | Apache license declarations |
| funasr 1.4.26 | MIT declaration; requires kaldiio |
| librosa 0.11.0 | ISC declaration |
| numpy 2.4.6 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 declaration |
| kaldiio 2.18.1 | Installed NTT evaluation agreement; commercial clearance unresolved |

**New review blocker:** installed kaldiio's LICENSE limits its stated grant to
internal evaluation of the named WAT 2017 methods and restricts transfer.
[Official upstream LICENSE](https://raw.githubusercontent.com/nttcslab-sp/kaldiio/master/LICENSE)
confirms these terms; the installed package is
[kaldiio 2.18.1](https://pypi.org/project/kaldiio/2.18.1/).
Do not label every installed component commercially cleared.

Installed does not mean active inference dependency. The unchanged narrator
passes `--no-denoiser`; installed `voxcpm/core.py` imports ZipEnhancer lazily only
when denoising is enabled. This suggests FunASR/kaldiio may be outside the approved
inference path, but no actual host import trace was collected. Establish the
actual runtime scope before excluding them. If used, resolve the license or
separately review a supported dependency isolation with narrator parity; do not
delete packages or rewrite the working host environment based on this report.

Host-only use, software redistribution and generated-media rights need separate
review. LGPL and bundled NVIDIA terms must be assessed for the actual use and
distribution plan. This bounded inspection is not complete transitive license
clearance or legal advice, and performs no acceptance on the owner's behalf.

Exact installed evidence digests (SHA-256):

| Evidence | Digest |
| --- | --- |
| kaldiio LICENSE | `ef2ebae3d9f21f550c6db96cb91de36050d4a03c37831c5af091c4814b6bf98a` |
| kaldiio METADATA | `654f114c1b49054c265e4e2e894f4c4489ee3b25430fa5e549d155ef3b7d24e9` |
| torch LICENSE | `3e289336d947fdf82f085f2a5ca757088084dd67d6530d46b4f02eb07461bb13` |
| torch NOTICE | `1c3dec6c0342c7ed9e12af59b296c7bb1d394af5cf881db74191cc8299efce5c` |
| torchaudio LICENSE | `32638e179931bfe551eabf67b0e67a13b483e166b58dd7263634ab7f89f396f5` |
| torchcodec LICENSE | `af2f7ef2b384a3e15ed6ced586e1a8316701c7bd828cc6ae4164f0dba8e5ac8f` |
| bundled libsndfile COPYING | `ad01ea5cd2755f6048383c8d54c88459cd6fcb17757c5c8892f8c5ea060f6140` |
| soxr METADATA | `4e2130ae330b85d863346ac935888e66d6816d8e934b6f4416614e8d22a4dc2e` |
| voxcpm/core.py | `aa8965af33ebbbc611b2bad18c67b99cfffac7b7b87900f49efa8d454f2755d2` |

Nine private evidence copies were readback-hash verified in a new FORGE-local
`collector-v9/rights-review-*` directory using the existing private provenance
directory's ACL. No private file contents were added to Git.

## Exact branding: BLOCKED_ASSET

Existing renderer pins remain unchanged:

| Required original | SHA-256 |
| --- | --- |
| Neon Cosmic Oxieg3n Emblem.png | `5da1076e095d61164e4de0a0b58905dea465936b92530f2ec1f8acdfcdd0db54` |
| Powered-By-Outro-Portrait.mp4 | `62496803360e377d81ab54b6970d94fcce3eee125f5d22c2fe08377dcf1b5c9b` |
| Powered-By-Outro-Landscape.mp4 | `3720a160cd8acb46c828d448cca740252fb8c6a80eba892f1573dc5b56479ee3` |

Current filename search covered the existing repository, FORGE collector-v9
evidence and collector backups; no matching original filenames were found.
Existing bounded host project-folder lookup covered three documented project
roots, depth six, 30 directories and 87 entries with no matches. The prior
203-metadata-file/backup review is preserved in the inspector repair report.
This is not a search of all host drives or Library. No accessible exact Library
reference was identified, and no download URL was guessed.

Owner follow-up: provide authorized Library materialization or private locations
for the three originals. Match bytes against these pins before acceptance.
No substitution, recreated approval, changed outro speech or fabricated hash is
acceptable. The complete 45-55-second branded/narrated acceptance remains blocked.

## Review scope

PASS: existing evidence read, bounded installed metadata/license inspection,
primary Apache/kaldiio terms consulted, nine private copy hashes verified,
exact renderer pins confirmed. Ponytail 5.3.3 FULL applied; documentation-only
diff reviewed for private data, unsupported clearance claims and unnecessary code.
No runtime code changed, so no regression suite was rerun for this report.
NOT TESTED: actual import set, CUDA inference, WAV/parity, full transitive legal
review, actual consent, remote transport or Library asset bytes.
