# V9 active narrator runtime and use-scope review

November 15, 2026. This is a bounded review for the existing, unmodified
BLACKHAT-BASE narrator and owner-controlled FORGE workflow. It distinguishes
private execution, generated media and redistribution. No inference, dependency
change, model download or host command was performed by this review.

## Evidence and owner listening

The owner reports that the diagnostic narrator sounds perfect and approves its
use in the project. This is a positive **owner-reported listening review** for
WAV SHA-256 `1083cd235598378fe4c7fc0556dcba1f9d3a9334b48620d522c2e826134dc6b7`.
No separate detailed observations or automated listening assessment are invented.
The decoded 3.04-second output, successful canonical exit and CUDA/bfloat16
selection remain the actual technical evidence in [HANDOFF](HANDOFF.md).

The private declaration hash is
`bc7d82dac515aadd72c061eebf9088df138f1e9ec746dd9b1287914eb6ede006`;
the reference/original generated WAV equality and selected text-design history
remain corroboration of synthetic origin, not an authenticated full generation
history. The fixed no-denoiser trace and lazy source branch support kaldiio,
FunASR, ModelScope and ZipEnhancer being inactive in the tested run. Their
installed licenses are preserved; denoiser activation or another execution path
would require a fresh review.

## Three different uses

| Use | Finding and obligations |
| --- | --- |
| Private narrator on BLACKHAT-BASE | The inspected top-level Apache/BSD/ISC/MIT terms, LGPL library terms and NVIDIA install/use grant do not establish a noncommercial-only restriction for this fixed path. Preserve installed notices and unmodified libraries; obey the existing NVIDIA license and hardware/use restrictions. This review accepts no new agreement on the owner's behalf. |
| Generated narration in monetized videos | The owner's voice/source authorization applies; software-library distribution conditions do not automatically turn a WAV into redistributed library code. Preserve media provenance and exact review hashes. Audio use remains subject to source rights and project publication approval; narration approval does not authorize a public upload. |
| Packaged application/dependency distribution | Separately incomplete. Identify actual shipped components, exact licenses and source/relinking/notice obligations before bundling host Python, model or native libraries. The existing FORGE installer does not thereby acquire approval to distribute the narrator environment. |

This is a scoped operational review, not a warranty of title, an exhaustive
transitive legal opinion, or clearance to redistribute every installed package.
The successful local smoke remains PASS even while distribution work is pending.

## NVIDIA terms and retained evidence

The installed Torch license/NOTICE are retained in the prior private rights
evidence. Torch's license file contains mixed third-party notices, including an
NVIDIA proprietary notice; its BSD headline is not a replacement for those terms.
The host Torch library directory contains CUDA/cuBLAS/cuDNN/NVRTC DLLs, but this
review does not claim every such DLL executed merely because it is present.

The official [CUDA agreement](https://docs.nvidia.com/cuda/eula/index.html) and
[cuDNN agreement](https://docs.nvidia.com/deeplearning/cudnn/backend/latest/reference/eula.html)
grant installation/use subject to their conditions and separately limit which
SDK portions may be distributed. A runtime bundle requires component-specific
redistributable eligibility and compatible downstream terms, retained notices,
and no removal of proprietary markings. Existing host installation and authorized
use are reused; no new license acceptance, redistribution or NVIDIA endorsement
claim occurs here. Do not copy the entire SDK as a standalone product.

## libsndfile, soundfile and soxr

`soundfile` and `soxr` occur in the actual Python trace. Installed soundfile
source uses CFFI `dlopen` for `libsndfile_x64.dll`; that separate DLL and LGPL-2.1
COPYING are present. The retained COPYING states that running a library-using
program is outside the restrictions on copying/distribution, and treats output
according to whether it actually contains a work based on the library. Normal
generated PCM audio is not a copy of the library merely because the library
wrote its WAV container.

For a distributed soundfile/libsndfile-based application, retain the wrapper's
BSD notice and the applicable LGPL text, identify the dependency, keep dynamic
replacement/relinking rights, and satisfy the applicable library source/source
offer obligations. Review modifications and static linking separately. The
[upstream libsndfile commercial-use FAQ](https://libsndfile.github.io/libsndfile/FAQ.html#Q21)
specifically describes dynamic-library use and license documentation. The
installed soxr metadata also declares LGPL-2.1-or-later; retain its notice and
review its binary/source provision if redistributed. No DLL or metadata was
modified or removed. GNU's license site timed out during this review; the
installed COPYING, previously hash-verified, is the actual retained text.

## Apache and other notices

[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) permits use with its
conditions. Redistribution needs the license, relevant notices and change
identification; it grants no general trademark rights. Retain the actual
VoxCPM/model-card evidence rather than inventing a missing snapshot LICENSE.
Prior package evidence covers Torch/torchaudio/torchcodec, NumPy, transformers,
tokenizers, Hugging Face Hub, librosa and text-normalization dependencies at its
recorded scope. Python import timing includes attempted optional imports and is
not a DLL profiler or complete package bill of materials. Do not infer a loaded
component solely from an attempted import or a directory listing.

## Manifest and operational acceptance

A new private candidate may record substantive review of this **fixed local-use
narrator and generated commercial-media scope**, with dependency redistribution
explicitly excluded. Supported evidence now includes owner voice authorization,
reference integrity, script review, actual independent runtime evidence and the
owner's exact-hash listening approval. No prior draft is overwritten. Additional
private review, smoke-receipt and import-log artifacts bind these findings.

Only actual host `validate-manifest` can establish acceptance of host paths,
current effective cache/ref and all artifact bytes. It necessarily hashes model
artifacts; this review does not repeat that operation remotely or claim a PASS.
Do not weaken the validator. A file prepared on FORGE with host-local paths is
an **unvalidated candidate**, not a deployed manifest or working service.

PASS: source/evidence review, owner-reported listening recorded, local-use/media
versus distribution obligations separated. NOT TESTED: actual host candidate
validation, listener/authentication, private HTTPS or FORGE transfer. Distribution
of narrator dependencies remains NOT CLEARED. Publication remains PAUSED.

Ponytail FULL and the installed review workflow were applied to the connected
manifest schema, evidence and claim boundaries. No runtime source changed and
no test suite/model inference was repeated for this report.
