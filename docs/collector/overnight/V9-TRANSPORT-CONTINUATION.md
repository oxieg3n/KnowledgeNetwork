# V9 transport continuation — November 15, 2026

## Current retention and uncertainty changes

Failed partial WAV downloads now remain retained. An existing completed joined WAV
can recover the original job only after decoded PCM/digest agreement with the
previously verified segments; mismatches hold and no new POST/ID is used. Focused
synthetic tests pass; they do not establish a real host transfer. Editor protocol
receipt finalization is serialized and preserves evidence on uncertainty. Host
recovery remains blocked by native D: namespace trust;9443 remains inactive.
See [current continuation](V9-RETENTION-AND-RECOVERY-CONTINUATION.md).

## Historical checkpoint review ? superseded smoke instructions

The remaining sections retain earlier checkpoint evidence. Their proposed smoke
and approval instructions are historical: the diagnostic was completed and the
owner approved its exact audio. Do not rerun it. Current host recovery/transport
gates are in HANDOFF and the continuation linked above.

Reviewed source checkpoint `3353a24efa3473c0e375dfec96cdd4fd757e6158` on
`feature/collector-v7-overnight`. Publication remains **PAUSED**. No inference,
host process, installation, credential provisioning or route change was performed
by this review. The passed model inventory and pipe repair were reused.

## PASS: bounded FORGE source and synthetic checks

The existing host and client already share the required contract. The host accepts
only the fixed narrator, bounded text and a 32-character lowercase hexadecimal
idempotency key. It runs the unchanged canonical script with structured arguments,
owns its process tree, serializes dispatch, persists receipts and holds uncertain
outcomes. Every API route requires the dedicated bearer. Audio retrieval rechecks
the durable digest. No additional provider or remote shell is needed.

The client connects to private pinned addresses with normal TLS hostname and
certificate verification, uses its separate VoxCPM2 Credential Manager namespace,
compares exact manifest provenance, verifies returned PCM against host metadata,
and derives segment captions from measured frames. Recorded submission intent
recovers by GET using the original host ID; it is never blindly POSTed again.

Executed in the existing FORGE project venv, Python 3.13.17, with `PYTHONPATH=src`:

```powershell
& ./.venv/Scripts/python.exe -m unittest discover -s tests -p test_collector_narrator_host.py
& ./.venv/Scripts/python.exe -m unittest discover -s tests -p test_collector_voxcpm2.py
```

Results: **22 host tests PASS** (20.136 seconds), **17 client tests PASS**
(3.001 seconds). These use synthetic inference and local fixture transport;
they do not establish real GPU execution, production host authentication,
cross-machine transfer, or listening. The optional native runner was not rerun.

## BLOCKED: actual route configuration

The real implemented `youtube_ops.collector_voxcpm2 status` command was exercised
both in the inherited process environment and after loading the four documented
user-scoped narrator variables into that process. It returned
`blocked_remote_narrator / BLOCKED_NARRATOR_CONFIG`, publication_eligible=false.
This fails before a host request and proves no remote API availability.

Do not invent a URL, pins, transport evidence or expected provenance. The private
route must come from the separately authorized deployed service, as described in
[Assistant operations](../ASSISTANT-OPERATIONS.md).

## Minimal next host action, after rights review and explicit approval

Reuse the complete [existing smoke procedure](NARRATOR-NEXT-INTEGRATION.md).
Approve one canonical-script inference into its fresh ACL-protected
`private-smoke-<guid>` directory under the existing host kit004. This creates
only the new WAV, logs and smoke receipt. It changes no canonical narrator,
installed package, model, service, networking or Gateway state. Verify the small
script/reference/CLI/ref/package bindings first; do not repeat the 4.96 GB model
inventory. A pin mismatch stops the action for review.

The procedure sets `PYTHONPROFILEIMPORTTIME=1` only for the child invocation and
restores its prior process value. The actual `voxcpm.exe` Python child inherits
that environment, so the canonical CLI imports are captured without a wrapper,
sitecustomize hook, changed script or changed third-party library. Preserve full
private stderr and inspect FunASR/kaldiio names together with source call paths
and successful complete execution. An absent name alone does not establish a
complete transitive license clearance. Do not automatically retry an uncertain
outcome. Successful CUDA device report plus actual generated PCM is runtime
evidence; it is not a kernel profiler trace or listening approval.

## Listener and route remain separate approvals

Only after substantive rights, runtime and voice review may a truthful private
manifest be completed. Reuse `validate-manifest`, `validate-spool`, interactive
`credential-save`, and `serve --manifest <actual-private-manifest> --spool
<actual-new-private-spool> --port 39110` from the existing procedure. This is a
loopback process, not an automatically installed Windows service. Validate missing
and incorrect bearer rejection and correct authenticated health locally first.

Inspect actual `tailscale serve status` read-only. If HTTPS 9443 is unused and
tailnet policy restricts access appropriately, separately approve only
`tailscale serve --bg --https=9443 http://127.0.0.1:39110`. Preserve all existing
root and 8443 routes. No reset, Funnel, public/firewall change or TLS bypass is
part of this action. No live status/route claim is made here.

## First remote acceptance should be one short request

After a real authenticated FORGE status PASS, use a fresh protected private
text file and a recorded fresh job ID with the existing `generate --job-id
<recorded-id> --text-file <actual-private-file>` command. Omitting segments makes
one host job. Retain its host ID, receipt, downloaded WAV, matching host/local
digest, measured frames/duration and exact reviewed provenance. Listening and
voice identity remain separate owner review.

The prepared full demo has 13 caption segments. The current client submits each
segment separately; the unchanged script loads the model for each host job.
Therefore that demo means **13 serialized canonical invocations**, not one warm
model call. Reserve it for the final accepted run; do not silently introduce a
persistent replacement or claim its total runtime has been measured. Reuse the
same original collector ID/text when reconciling any uncertain request.

The existing native fixture can consume the completed real `narration.json`
through `--narration-receipt` for narration/caption/music attachment only. Its
builder remains a fixed 50-second unbranded timeline without a bookend option.
Full branded native assembly and body/caption offsets must still be exercised
using the existing structured native operations once the exact approved assets
and real narration exist. See [native readiness](V9-BRANDING-CONTINUATION.md).
No existing synthetic fixture is relabeled.

## Review and limits

Ponytail FULL 5.3.3 and installed `ponytail-review/SKILL.md` were read/applied.
Documentation-only diff reviewed against connected host/client source and tests
for unsupported claims, private evidence disclosure and unnecessary new code.
No source defect requiring a change was established in this bounded review.
No UI changed; no new native UI or browser design gate is claimed.

NOT TESTED: actual host import trace, rights clearance, real inference,
listening, host service/9443/authentication, cross-machine WAV, native attachment
and final video, reboot or scheduled Assistant reliability. Existing backups and
publication controls were untouched.
