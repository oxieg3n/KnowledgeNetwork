# V9 narrator rights continuation

Subsequent owner-run diagnostic: **PASS host smoke only**. See the newest
[handoff entry](HANDOFF.md) for exact run/WAV/log hashes. Exit 0, valid 3.04-second
PCM and CUDA/bfloat16 selection were observed. The parsed trace has no kaldiio,
FunASR, ModelScope or VoxCPM ZipEnhancer imports and confirms denoising disabled.
Together with the source branch this supports those components being inactive
in this exact run, superseding the missing-runtime-evidence blocker below.
Active-component/redistribution review and listening remain separate; no blanket
commercial clearance, manifest promotion or remote API success is asserted.

November 15, 2026. Read-only BLACKHAT-BASE file inspection from FORGE through
the previously used redirected drive; no host execution, inference, environment
change, service, route or model inventory rerun. Publication remains **PAUSED**.

## Owner authorization and source corroboration

PASS: the private `reference-rights-private.md` exists at the canonical narrator
directory and was read. Its actual SHA-256 is
`bc7d82dac515aadd72c061eebf9088df138f1e9ec746dd9b1287914eb6ede006`.
It authorizes the declared original synthetic voice for commercial narration and
monetized channel use, subject to source and software obligations. It explicitly
leaves independent provenance, commercial-rights acceptance and runtime acceptance
pending. A typed declaration is owner authorization, not independent historical
proof.

PASS: canonical `reference.wav` still hashes to
`050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44`.
The retained original generated WAV also exists and has this exact digest.
Canonical script SHA-256 remains
`98b75e5313d72d7aa65d160b41ebcb8726968bb7044700e2cffb510b5a72f189`.

Relevant retained generation history contains text-control `voxcpm design`
commands and a subsequent copy from the original output to the canonical
reference. The inspected installed CLI rejects prompt/reference audio in design
mode. The selected text describes a general documentary voice; it does not name
a person to imitate. These facts corroborate the declared synthetic origin and
provide no indication of third-party speaker conditioning in the recorded design
commands. Shell history records entered commands, however, and is not an
authenticated successful-execution receipt or complete proof against every
possible earlier source. Do not infer a human-speaker consent record.

New evidence is retained privately on FORGE, including hash-verified declaration,
current script/CLI/core/denoiser source copies, strictly selected generation/copy
history, and review findings. Original host files are unchanged. A private draft
manifest contains the canonical declaration as `consent_evidence` with its actual
digest and 53 existing-schema artifacts. All seven acceptance booleans remain
false; it is deliberately **not accepted or deployable**. Model artifacts reuse
the existing passed inventory, rather than repeating its 4.96 GB hashing operation.

## Runtime license scope remains unresolved

The current installed CLI passes `load_denoiser=False` for the canonical
`--no-denoiser` option. Current `voxcpm/core.py` imports `ZipEnhancer` only inside
the enabled-denoiser branch; `zipenhancer.py` imports ModelScope. This supports
the proposed inactive-denoiser boundary, but static source inspection does not
prove the complete runtime import set or absence of another import path.

The installed kaldiio license restriction remains unresolved. The
[upstream license](https://raw.githubusercontent.com/nttcslab-sp/kaldiio/master/LICENSE)
still states an internal evaluation grant and transfer restrictions; the
[exact-version PyPI record](https://pypi.org/project/kaldiio/2.18.1/) was also
consulted. No package was removed or modified. Commercial runtime clearance
remains **BLOCKED** until the actual canonical run's import evidence is reviewed.
If FunASR/kaldiio participates, stop commercial clearance and review a separately
authorized licensed solution.

[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0) redistribution conditions
require license and applicable notice retention and identification of modified
files. Host-local execution, distributing a runtime environment, and rights in
generated audio require separate assessment. The prior BSD/LGPL/NVIDIA component
findings remain applicable; neither Apache's top-level declaration nor an absent
runtime import supplies blanket transitive legal clearance. The pinned model-card
web page could not be opened in this review; its previously verified private copy
and digest remain the evidence, without a new online verification claim.

## Narrow next gate and review

Complete the bounded canonical-script smoke described in
[NARRATOR-NEXT-INTEGRATION.md](NARRATOR-NEXT-INTEGRATION.md) only after the owner
authorizes that exact host action. Retain its private import-time log, CUDA
selection/exit code, decoded WAV frames and digest; inspect FunASR/kaldiio use.
No automatic retry, listener or network change follows from smoke permission.
Voice identity and audio quality still need actual listening.

PASS: declaration read/hash, reference/original equality, script identity,
selected source-history corroboration, small installed-source inspection,
private evidence copy/readback hashes, and fail-closed draft preparation.
NOT TESTED: live runtime imports, CUDA inference, new speech, listening,
cross-machine transfer, complete transitive license review or commercial legal
acceptance. Documentation-only change; no repeated media/worker suite.
Ponytail FULL review checked truthful claims, evidence boundaries, reuse,
private-data exclusion and absence of changes to approval controls.
