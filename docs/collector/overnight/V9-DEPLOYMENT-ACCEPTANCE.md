# V9 restricted deployment acceptance — owner-side execution

November 15, 2026. Owner authorization now covers the existing restricted
loopback narrator, one new private spool and app-specific CredMan bearer, and
private HTTPS 9443 only after all stated prerequisites pass. It does not supply
a host execution channel. This session has redirected-drive file access only.
No host listener, credential, route or inference was executed by this review.

## Current verified state and remaining gates

- The completed single diagnostic is reused; do not run it again. Owner reports
  positive listening approval for exact WAV SHA-256
  `1083cd235598378fe4c7fc0556dcba1f9d3a9334b48620d522c2e826134dc6b7`.
- The three actual host-kit modules below hash-match current source, without
  copying or modifying host files:

| Module under kit004 `src/youtube_ops/` | SHA-256 |
| --- | --- |
| `collector_narrator_host.py` | `ad04e4b5d2abf958a9eb06f06ef5a5f8f560dd8415b96a449808bd40460a7d6c` |
| `collector_narration_common.py` | `1c3c5b995ccccba590385bd7c4518eb7487954260bd80ad3ac6627b72de87344` |
| `collector_credentials.py` | `14252242504c2b71cdd3f2a96956ec78f1fd8ee15faf453ffc2dad28571c742c` |

- FORGE's actual `collector_voxcpm2 status` still returns
  `BLOCKED_NARRATOR_CONFIG` before network. No remote success is claimed.
- Existing saved tailnet peer metadata is November 14 evidence. It does not
  establish current host Serve configuration, port availability or effective
  access policy. **These three prerequisites remain unverified.**
- A rights-reviewed scoped local-use manifest candidate now exists privately at
  `C:/admin/collector-v9/local-use-review-v9-001/narrator-manifest.LOCAL-USE-CANDIDATE.private.json`,
  SHA-256 `42f270ac0232c24c200df0a02401df97b7f1c2796ddeb519ce35eda2a9924d84`.
  It is **not host-validated yet**. The old deliberately unreviewed draft is
  preserved; it is not used for service startup.

## Exact owner sequence

The prepared copy/paste command file is
`output/Narrator-Restricted-Deployment-Owner.txt`. It contains numbered blocks
for local BLACKHAT-BASE PowerShell sessions and a FORGE continuation. It is a
procedure, not an executed receipt or an installer. No execution-policy bypass
is used. Stop at the first failure, preserving private receipts. Do not restart
or resubmit an uncertain media job to force progress.
Procedure SHA-256:
`3cf6f0b80f780ff5c7c89370b015f282fef8849eb65c82e042823712ef4d9fbf`.
The owner command file is ASCII, safe to display with Windows PowerShell5.1's
default `Get-Content` encoding. Recopy only executable blocks, not stage headings.

1. Stage1 creates exactly one spool at
   `D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001`.
   It refuses an existing directory. Return that path so FORGE can copy the
   three hash-pinned files from `C:/admin/collector-v9/local-use-review-v9-001`
   into the spool's host-local `review` directory: the candidate manifest,
   `operational-review.private.json` and `active-runtime-review.md`.
   Their exact hashes are in `delivery-hashes.private.json`; root verifies the
   copied bytes before stage2. Do not overwrite drafts/originals. The manifest
   pin is built into stage2; a FORGE-only path is not a host manifest.
   Run real `validate-manifest`: it checks current selected ref/checkpoint and
   all artifacts, including expensive model hashes. This is the required service
   acceptance gate, not another model inventory. Never set review booleans just
   to pass it.
2. The block creates one fresh protected spool, validates its DACL, checks 39110
   is free, and refuses an already provisioned host credential. Generate one
   new 32+ character app-specific secret in the owner's password manager; enter
   it only at the existing hidden `credential-save` prompt. Do not use a command
   argument, environment variable, transcript, log, chat or unrelated root key.
3. Start the existing `serve --port 39110` in that foreground host terminal and
   keep it running. This installs no Windows service/autostart. In a second
   terminal, verify the actual listener is only 127.0.0.1:39110 and execute the
   prepared local auth tests. The test reads the secret from host CredMan and
   reports only status/results. Missing and incorrect bearers must return401;
   the real bearer must return fixed narrator health and matching provenance.
   Deliberately invalid caller fields must return400 without enqueuing a job.
4. Capture `tailscale serve status --json` privately. Verify 9443 is absent and
   preserve the existing root/Gateway routes. Obtain/review the **effective**
   tailnet policy and tests: only the intended FORGE source may reach the host
   on TCP9443, with other peers denied. A narrow additional allow rule does not
   cancel a broader wildcard allow rule. Peer presence, DNS, Serve status and an
   operator typing “verified” are not policy proof. Stop before the route command
   if policy evidence is absent or access is broader; do not modify unrelated
   policy to proceed under this procedure.
5. Only after local auth and these preconditions pass, run the single existing
   Serve command and capture post-state. The supplied route is private Serve,
   never Funnel. Compare all other routes before/after. Existing Gateway stays
   intact. Derive the actual HTTPS origin and private address pins from this
   verified host/tailnet evidence, never from a guessed hostname.
6. Create the actual protected FORGE route JSON per the current schema in
   [Assistant operations](../ASSISTANT-OPERATIONS.md). Set exact host provenance
   from `manifest-validation.private.json`, and hash the real transport review
   evidence for `transport_evidence_sha256`. Keep addresses, policy, credentials
   and route evidence private. Enter the same dedicated secret at FORGE's hidden
   credential prompt in the correct user account. Run `status`; require PASS,
   matching provenance, ready host and no execution hold.
7. The FORGE block stops after credential entry and `status`. Root first reviews
   actual PASS, then writes a fresh one-sentence text and **records one job ID
   before submission**, and calls `generate` without segments: exactly one host
   narration job. Do not run the prepared 13-segment full demo yet. Preserve the
   collector receipt and host job ID. If interrupted, recover that same ID; do
   not create a new acceptance directory/ID to retry uncertain work.

The existing implementation supplies schema/input denial, fixed script/voice,
owned process tree, single worker queue, durable idempotency, WAV digest checking,
cancellation and uncertain-outcome hold. Previous synthetic negative tests remain
applicable; source review is not live host acceptance of all these properties.
After the one real job, compare host receipt/spool WAV and FORGE receipt/WAV
digests, sample frames/duration and exact provenance before recording
`REMOTE_NARRATION_PASS`. A host-local smoke or copied file does not count.

Official [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve)
and [tailnet policy syntax](https://tailscale.com/docs/reference/syntax/policy-file)
were consulted for route and access-control boundaries. Tailnet grants are
additive; a broad existing allow must be accounted for in effective-policy review.

## Checks and limits

Ponytail5.3.3 FULL and installed review skill applied to existing host/client,
credential handling and procedure. No production source change was necessary.
All five prepared PowerShell stages and two embedded Python blocks parsed on
FORGE without executing them. The current Serve gate self-check passed five
absent/present TCP/Web/nested9443 cases and four invalid JSON shapes. Stage4
parses current Serve state, rejects configured9443, and queries all Windows
listeners with terminating errors before filtering ports; command/query failure
is not interpreted as a free port. These are procedure checks, not host tests.
No new paid service, package or control framework.
Publication remains PAUSED; no media uploaded. PR20 remains draft/unmerged.

BLOCKED: actual host execution, host-validated local-use manifest, live loopback/auth,
current Serve/9443/effective-policy proof and scoped bearer provisioning.
NOT TESTED: real HTTPS FORGE request, new remote WAV, live cancellation/restart,
autostart/reboot, sustained service reliability or final video acceptance.
