# V9 private tailnet remediation review

## Current state ? v5 APPLIED AND POST-VERIFIED; route remains held

The owner explicitly approved **v5 policy only**. The coordinator performed one conditional policy POST with HTTP 200, after a fresh complete inventory comparison and matching baseline ETag. There was no POST retry or automatic rollback. No narrator HTTPS route was started.

Approved submitted bytes retain SHA-256 `c96c6e7c4682625ae1b6e0aba21e52bd9d697b6c76b71d539a8f0cc986235d19`. The service stored and returned a different representation, SHA-256 `35697bcb6e06a9b2047d6056ab847fcff31f2d054ca8da7ba8e6a97222b10335`. The initial byte-digest gate correctly stopped for review. Independent private comparison then verified exact parsed-object equality across the submitted candidate, POST response and GET readback: all five policy sections, every literal value and type, all array ordering, twenty tests and 400 assertions match. Only representation normalization is established; neither hash was overwritten or relabeled.

Private evidence is retained in `%USERPROFILE%/KnowledgeNetworkCollector-Private/policy-apply-001`, including `independent-normalization-review.private.json` and `normalization-typed-equality.private.json`. Official non-applying post-application validation of the actual stored representation PASSED all twenty tests and 400 assertions. All ten post-application previews independently match the pre-approval source/destination/posture values exactly; only representation-dependent line numbers were excluded. Private evidence is retained in `policy-postapply-001/independent-postapply-review.private.json`. Native narrator, authentication, port and route gates remain separate. Publication remains PAUSED.

### Credential capability finding

The single explicitly approved policy POST was accepted with HTTP 200. Therefore the saved application API credential has effective **policy-write capability**; its Credential Manager target ending in `ReadOnly` does not make it read-only. The reusable review helper still exposes only fixed read and non-applying validation/preview operations. The separate private one-off writer was limited to the exact approved v5 bytes and one conditional attempt. No further policy writes or credential permission changes were performed.

For ongoing audits, the owner should replace/revoke the broad API credential and provision a strictly scoped read-only OAuth access token. This requires credential administration; v5-only approval did not authorize creating broader permissions or another policy update. Do not claim issued read-only scope based on the storage target name. Credentials remain outside Git, command arguments and chat.

## Final v5 review ? retained pre-application owner review

**PASS at the pre-application review checkpoint:** reviewed current-inventory impact and official non-applying evaluation. The subsequent owner-approved application is recorded above. Exact candidate SHA-256: `c96c6e7c4682625ae1b6e0aba21e52bd9d697b6c76b71d539a8f0cc986235d19`; reviewed live baseline: `a143952dfa2a51062e4bf003801b597c47fcc4edcb80d5ada9a4992c3b7fd86c`.

Actual API evidence is retained at `%USERPROFILE%/KnowledgeNetworkCollector-Private/tailnet-api-live-002`: five devices, ten addresses, and all five advertised/enabled route array pairs explicitly present and empty, including zero advertised/enabled exit-node defaults.

The actual v5 official validation passed twenty tests and 400 valid same-family assertions. All ten official previews were independently reviewed against the pinned source: eight nonhost targets retain the wildcard nonhost grant; two host targets match the intended wildcard protocol-complement rule and separate FORGE-only TCP 9443 rule. IP:port previews are protocol-agnostic, so the host's wildcard match is expected for preserved UDP/ICMP and other TCP ports. The official TCP-negative and UDP-positive assertions distinguish those cases. Current HTTPS 443/8443, Gateway and project SSH permissions remain preserved. No existing service or Serve configuration was changed during review.

The private owner approval summary is `%USERPROFILE%/KnowledgeNetworkCollector-Private/approval-review-v5.private.md`, supported by `tailnet-policy-approval-v5.private.json` and `policy-validate-004`. V1?V4 proposals, failures and the unchanged-policy positive diagnostic remain retained. The candidate's bytes were not modified after its hash was fixed.

The protocol claim is limited and explicit. Official [grant syntax](https://tailscale.com/docs/reference/syntax/grants) and [client filter defaults](https://github.com/tailscale/tailscale/blob/main/wgengine/filter/tailcfg.go) define the original wildcard set as TCP 6, UDP 17, ICMPv4 1 and ICMPv6 58. The candidate retains that set; it does not remove an original SCTP/GRE permission. An independent selector comparison examined protocols 0?255 across 128,000 same-family boundary cases. ICMP preservation is supported by source semantics, not a native ICMP test or additional official ICMP assertions. Supported TCP service ports 1?65535 are covered; **reserved TCP destination port 0 is not preserved at the narrator host**, because the official evaluator rejected the explicit zero-based range. Owner approval must accept that packet-domain limit alongside static-inventory maintenance. There is no claim that all possible raw packets remain unchanged.

The owner approval review explicitly disclosed static-inventory maintenance: new/renumbered destination devices and future approved subnets require reviewed updates instead of the old automatic wildcard inclusion. New sources retain existing wildcard access to current destinations outside host TCP 9443. Remove/update the recorded FORGE source-IP allowance before device deletion or address reassignment. Alternatively, request a separately reviewed dynamic-identity design. This is an availability/identity-maintenance boundary, not a claim of preserved future wildcard behavior.

Immediately before any application, re-fetch current policy and full inventory/routes and require the reviewed baseline digest and coverage; stop on drift. Current API evidence is interval-based, not atomic. Missing API tag fields are retained as a limitation, but no current network group/tag/user selector is changed; SSH remains unchanged. Policy approval does not authorize unrelated routes, public access, publication or PR merge. Publication remains PAUSED. The helper has no policy-application endpoint.

## HISTORICAL proposal and diagnostic evidence ? superseded by current status

All checkpoint-specific pending/blocked statements below describe their historical stage. The authoritative current result is the final v5 review above. Original proposals and diagnostic evidence remain preserved.



## Historical API continuation ? v3 checkpoint

The coordinator's fresh `tailnet-api-live-002` capture **PASS_CAPTURE_ONLY** retained five devices and all five route responses. Every device has explicit advertised/enabled arrays, all empty; both advertised and enabled exit-node default-route counts are zero. Fresh live policy bytes match the retained private policy SHA-256 `a143952dfa2a51062e4bf003801b597c47fcc4edcb80d5ada9a4992c3b7fd86c` exactly. Modern device IDs match the CSV IDs, and each individual device's addresses match; the legacy numeric IDs use a different schema and were not confused with the modern IDs. All ten addresses match the v2 inventory and saved host map.

Explicit API fields show all five devices authorized and none external/shared-in. Device user fields are present. The API omits `tags` on all five records; this is recorded as missing metadata, not proof that devices are untagged. User-role listing is not necessary to compare the current wildcard network grant with this IP-only proposal because neither uses user/group/tag selectors, and the SSH policy is unchanged. These observations do not certify unrelated identity management or future policy changes.

The first official non-applying v2 validation returned HTTP 200 with a failure message rejecting the port range beginning at zero. The helper correctly returned BLOCKED and did not run previews or apply anything. That evidence remains in the protected owner-profile `policy-validate-001` directory. V3 changes only `tcp:0-9442` to `tcp:1-9442`; all other selectors and embedded tests remain unchanged. Its supported service-port domain is 1?65535, consistent with the actual evaluator's rejected zero range.

The v3 proposal is protected under the owner-profile `KnowledgeNetworkCollector-Private` directory as `proposed-inventory-v3.private.hujson`, with private diff and review receipts. SHA-256: `5659bedf4e0e70c2e5a2b8ef1eb87f085c8d41210c7c79e80edee55fc3b6208b`. An independent evaluator of the parsed v3 grants/IP set passes all 6,553,500 inventoried address-pair/TCP-port combinations. This remains an offline assertion. Official v3 validation and preview are pending; v1/v2 evidence is retained. No policy or route was applied.

### V3 official result and v4 diagnostic representation

Official v3 validation also returned HTTP 200 with test failures. All twenty protocol-specific tests reported no matching IP protocol. This is not recorded as a passing policy or as a proven source/destination permission result. V4 changes only the test protocol representation from named TCP/UDP aliases to the documented IANA numeric strings `6` and `17`; all grants, destinations and accept/deny assertions are retained unchanged. V4 SHA-256: `716ae89fb43fdec57438bca3dbbeff331b3dc3d08bc3961501c1be46a9d0ef94`. This is a diagnostic hypothesis pending official evaluation, not an established explanation or a weaker test. V3 and earlier evidence remain intact; no application occurred.

### V4 diagnosis and v5 same-family test correction

The numeric-protocol v4 experiment failed, while a separate diagnostic using the unchanged live grant and two valid IPv4 HTTPS controls passed official validation. Correlating every private error with its source and destination revealed the precise cause: all 400 errors tested an IPv4 source against an IPv6 destination, or the reverse. There were zero same-family test failures. Thus the evidence does not implicate protocol aliases, the official evaluator or candidate access grants.

V5 retains all twenty TCP/UDP test cases and all 400 physically valid same-family assertions across the inventoried IPv4 and IPv6 addresses. It removes exactly the 400 impossible cross-family packet assertions corresponding to the official errors. Grants, IP set, SSH and node-attribute sections are unchanged from v3, and the original named protocol aliases are restored. Both address families retain positive FORGE, negative unauthorized-peer and service-preservation assertions. This corrects the test traffic model; no permission or valid security assertion was relaxed.

V5 SHA-256: `c96c6e7c4682625ae1b6e0aba21e52bd9d697b6c76b71d539a8f0cc986235d19`. The protected owner-profile proposal, diff and review receipt retain the complete reasoning and earlier versions. Official v5 validation/preview remain pending. Nothing has been applied.

## Read-only Admin API fallback

The bounded FORGE helper is `src/youtube_ops/collector_tailnet_review.py`. It implements credential-save, capture, and hash-pinned non-applying validation/preview. It never applies a policy, changes routes, provisions OAuth clients, accepts arbitrary URLs/methods, or starts host services. The owner saved a new dedicated credential. The coordinator's first actual capture authenticated successfully and retained five device records and five route responses, then returned BLOCKED at the policy-format guard. That guard incorrectly rejected legal leading HuJSON comments and is now fixed with a regression fixture. Preserve that failed receipt; only a fresh coordinator-run capture can establish completed capture acceptance. Ten mocked HTTP/Credential Manager tests pass; no live API result is implied.

An authorized administrator must provision a dedicated short-lived OAuth **access bearer token**, using only `devices:core:read`, `devices:routes:read`, `policy_file:read`, and its required `devices:posture_attributes:read` dependency. Do not supply an OAuth client secret, auth key, Gateway credential, broad administrator token, or token with policy/device write scopes. The helper cannot independently attest the token's issued scopes. Its request allowlist contains only fixed GET reads and the two explicitly non-applying policy evaluation endpoints; the policy mutation endpoint is prohibited. API access tokens and OAuth access tokens support Bearer authentication; client secrets and device auth keys are rejected before Credential Manager writes. Empty, short, oversized, whitespace and non-ASCII inputs receive stable API error codes without echoing input. See the official [credential scope reference](https://tailscale.com/docs/reference/trust-credentials) and [OAuth client guidance](https://tailscale.com/docs/features/oauth-clients). Additional `users:read` may be needed for a later complete identity review; this helper does not call the users endpoint and reports identity completeness unverified.

Run the save command in an interactive FORGE terminal as the same Windows user that will run capture. The prompt hides input; noninteractive/echo fallback is rejected. Paste the access token only at that prompt. It is stored solely at the fixed user-scoped Windows Credential Manager target `KnowledgeNetworkCollector/TailscalePolicyReview/ReadOnly`. Successful output is only `{"status": "SAVED"}`. Do not paste tokens into command arguments, chat, environment variables or files.

```powershell
Set-Location 'C:/Admin/Projects/KnowledgeNetwork'
$env:PYTHONPATH = 'src'
& '.venv/Scripts/python.exe' -m youtube_ops.collector_tailnet_review credential-save
```

After the dedicated token is saved, capture into a **new** child directory of an existing private local folder. Use the protected owner-profile project directory established and checked by the coordinator; the child below must not already exist. Do not use the older C:/admin proposal directory for fresh API evidence: native review found an unsafe ancestor replacement permission. Original proposals there remain preserved and hash-pinned; no unrelated ACL is changed. The helper rejects UNC/reparse paths, unsafe parent ACLs, existing targets and unsafe ancestor replacement permissions. It creates a protected owner/SYSTEM/Administrators-only output directory and exclusive files.

```powershell
$tailnetReviewOutput = Join-Path $env:USERPROFILE ('KnowledgeNetworkCollector-Private/api-capture-' + [guid]::NewGuid().ToString('N'))
& '.venv/Scripts/python.exe' -m youtube_ops.collector_tailnet_review capture --output $tailnetReviewOutput
```

The capture request set is GET `https://api.tailscale.com/api/v2/tailnet/-/devices?fields=all`, GET `/api/v2/device/<validated-id>/routes` for each device, and GET `/api/v2/tailnet/-/acl` requesting HuJSON. TLS certificate/hostname checks remain enabled, environment proxies are ignored, and redirects are rejected. Capture has a 90-second cooperative/socket deadline, an 8-MiB per-response cap, at most 1,000 devices, and no pagination assumption: unexpected continuation/shape blocks coverage. DNS resolution uses the Windows resolver and is not separately preemptible. Required `advertisedRoutes` and `enabledRoutes` arrays must be present for every device; errors or absent arrays remain BLOCKED, never interpreted as empty. Approved routes can exist without current advertisement and are retained independently. The official [device client](https://github.com/tailscale/tailscale/blob/main/client/tailscale/devices.go) and [route client](https://github.com/tailscale/tailscale/blob/main/client/tailscale/routes.go) document these fields and semantics.

Raw successful API responses, exact file hashes and route coverage remain private; stdout contains only counts/status/error codes. Expired credentials, denied scopes or route failures produce a blocked receipt. `PASS_CAPTURE_ONLY` means the bounded inventory/policy responses were captured, not that the policy is safe or officially evaluated. Policy syntax/effective authorization review, complete identity coverage, non-applying official validate/preview, and the future-device maintenance decision still remain. Non-applying validation and preview are now implemented using the primary-source contract below; no policy mutation endpoint exists in this helper. There is no automatic credential refresh or retry.

### Hash-pinned non-applying evaluation

`validate` first verifies the private local policy file, its safe parent/ancestor ACLs, absence of links/reparse points and exact required SHA-256. It captures those exact bytes once and sends them only to Tailscale's `POST /api/v2/tailnet/-/acl/validate`. A nonempty validation message, errors, warnings or data blocks acceptance even with HTTP 200. Successful validation is labeled `PASS_OFFICIAL_VALIDATION_ONLY`.

For a JSON candidate with embedded tests, the helper derives at most twenty unique literal destination IP:9443 previews from those pinned tests, then posts the same captured bytes to `/acl/preview?type=ipport&previewFor=<encoded-target>`. Responses must echo the expected target/type and contain matches; complete response bytes stay private for rule review. A successful preview capture is **not** an automatic access-security PASS. HuJSON that cannot be decoded by the strict standard-library JSON parser can still be sent for official validation, but preview target derivation remains blocked. The helper never retries, never submits POST `/acl` without a validation/preview suffix, and never follows redirects.

The coordinator must first stage an exact hash-verified candidate in the safe protected owner-profile project folder; do not weaken the ACL guard to read the older C:/admin location. Example syntax, with the exact reviewed hash and actual protected path supplied by the coordinator:

```powershell
$tailnetPolicyFile = Join-Path $env:USERPROFILE 'KnowledgeNetworkCollector-Private/proposed-inventory-v5.private.hujson'
$tailnetValidationOutput = Join-Path $env:USERPROFILE ('KnowledgeNetworkCollector-Private/validation-' + [guid]::NewGuid().ToString('N'))
& '.venv/Scripts/python.exe' -m youtube_ops.collector_tailnet_review validate --policy-file $tailnetPolicyFile --policy-sha256 'c96c6e7c4682625ae1b6e0aba21e52bd9d697b6c76b71d539a8f0cc986235d19' --output $tailnetValidationOutput
```

This command is a non-applying evaluation of the retained v5 candidate; it does not imply that v5 has satisfied live-inventory or future-device review. Replace neither the candidate nor its pin merely to make a test pass. Capture and validation receipts include UTC start/end timestamps; capture is explicitly an interval rather than an atomic server snapshot. No live call has been made by the helper's implementation agent.

Authentication and evaluation contracts were checked against the official [API reference retained in Tailscale v1.50](https://github.com/tailscale/tailscale/blob/v1.50.0/api.md), the [current official preview client](https://github.com/tailscale/tailscale/blob/main/client/tailscale/acl.go), and the [current scope reference](https://tailscale.com/docs/reference/trust-credentials). The historical reference distinguishes a JSON-array test against current policy from a JSON-object hypothetical candidate; this helper sends the full candidate object bytes. Current policy-file read scope explicitly permits non-applying validation and preview.

## Inventory continuation ? current proposal v2

**PASS for supplied inventory coverage; BLOCKED for application pending official validation/preview and live freshness checks.** The owner supplied a complete-device CSV with five unique records and ten unique Tailscale addresses. Its address set exactly matches the previously captured host network map. Columns explicitly include device IDs, manager/creator, tags, subnet-router status, approved and unapproved subnet routes, exit-node capability and sharing. Route columns are empty, and the separate route statement explicitly reports no subnet routes. Empty cells alone were not treated as proof. Exit-node cells are blank; this is not an independent exit-node verification, and no exit-node internet permission was introduced. The existing wildcard grant excludes that special internet destination scope.

Freshly reread private policy bytes still hash to `a143952dfa2a51062e4bf003801b597c47fcc4edcb80d5ada9a4992c3b7fd86c`. CSV hash: `02fac66d7b351278599f1b476464b93088cb2baa3ed5ee838bb68723a66bd9f1`; route statement hash: `011ba761bc27b55bc13395815ef0ed4c61edbe846d7fb0edba1a55791a23f545`.

The original proposal and provenance remain intact. New private files in the same protected directory are `proposed-inventory-v2.private.hujson`, `proposal-inventory-v2.private.diff`, `coverage-inventory-v2.private.json`, `offline-inventory-v2.private.json`, and exact copies of the supplied inventory, route statement and freshly read policy. Complete v2 proposal SHA-256: `6874bc0f006e8acf0fa2623f289dd0b727ee269178fd97c6a2ab74aac915b0a8`.

V2 uses the supplied full-device address inventory instead of inferred network-map ranges. Three grants preserve wildcard access to the inventoried nonhost destinations, preserve narrator-host access outside TCP 9443, and permit only FORGE addresses to host TCP 9443. Twenty embedded official-format tests now include every inventoried source/destination address, with positive/negative host TCP 9443 checks and preservation checks for HTTPS 443/8443, Gateway SSH, project SSH, neighboring ports and UDP 9443. SSH and node-attribute policy sections remain unchanged. The original wildcard rule was removed from the candidate, rather than left overlapping the restriction.

PASS offline: independent subset evaluation of 4,000 source/destination/protocol boundary cases, plus exact TCP port-set comparison covering 6,553,600 address-pair/port combinations. These are local assertions against the parsed candidate, not Tailscale results. ICMPv4/IPv6 wildcard equivalence remains an explicit assumption requiring official evaluation. Existing services and application restrictions were not exercised or changed by these tests.

Remaining precise limitations: the exports have no independent live control-plane freshness receipt; the private policy file is a saved export; official syntax/test validation and per-identity preview have not run. Static destination enumeration also changes behavior for new or renumbered devices and future approved subnet routes: they require an inventory update, while the old wildcard would include them automatically. The owner/coordinator must accept that maintenance boundary or approve a dynamic-scope design before application. This is not a claim that unrestricted future wildcard behavior is preserved. Current inventory fields are adequate to draft this current-device candidate; do not ask again for those already supplied fields.

Next: verify the current control-plane policy and inventory still match these retained exports, validate and preview v2 through an authorized Tailscale admin context without saving it, verify protocol equivalence and negative identities, and review the static-inventory boundary. Only after those checks pass may the coordinator consider policy application and the separately gated 9443 route. No policy, Serve route or host service was changed during this review.

## Earlier snapshot review ? retained provenance

Status: **BLOCKED — proposal only; do not apply.** Publication remains paused. Neither the tailnet policy nor any Serve route was changed.

The complete supplied private policy has one network grant with wildcard source, wildcard destination and wildcard IP permissions. There are no network ACLs, groups, tag owners, host aliases or additional overlapping network grants. Its separate SSH section does not restrict HTTPS. Consequently the current policy permits unauthorized peers to reach a proposed host TCP 9443 route. Adding a narrow FORGE grant cannot undo the existing broad grant: permissions are additive. Existing SSH and node-attribute sections are preserved in the draft.

The original private policy SHA-256 is `a143952dfa2a51062e4bf003801b597c47fcc4edcb80d5ada9a4992c3b7fd86c`. Private artifacts are in `C:/admin/collector-v9/tailnet-remediation-v1`: `original.private.hujson`, `proposed.private.hujson`, `proposal.private.diff`, `observed-state.private.json`, `review.private.json`, and `offline-evaluation.private.json`. They contain private addresses and must not enter Git. The draft SHA-256 is `bf0f682a24f41b57bcae832079c3b0eb8c251dd48130a07587234c9f9f983cc4`.

The complete draft replaces the broad network grant with three grants: preserve wildcard permissions to observed destinations other than the narrator host; preserve host access other than TCP 9443; allow only the observed FORGE addresses to host TCP 9443. An IP set subtracts both host address families from the observed destination scope. Twenty embedded policy tests cover observed positive/negative sources, both host address families, existing HTTPS 443/8443, Gateway SSH transport, the dedicated project SSH transport, neighboring TCP ports and UDP 9443. Existing application-level Gateway restrictions remain independent and unchanged.

This is a reviewable current-observation candidate, **not an exact general replacement for the wildcard policy**. The saved host network map contains five nodes, but local status is not an authoritative complete device and approved-subnet-route inventory. Unobserved or future approved destinations could lose access with an enumerated scope. Conversely replacing the scope with all IPv4/IPv6 addresses minus the host could broaden permissions to destinations excluded by the original wildcard. The draft deliberately avoids that broader substitution. No claim of complete access preservation is made.

PASS: original bytes retained; all policy sections inspected; unchanged SSH/node-attribute values checked; private draft and diff retained; an independent local subset evaluator checked 2,000 observed-address TCP/UDP cases against the parsed generated grants/IP set. These checks support only the observed matrix. They do not implement Tailscale identity resolution, route approval or the official policy evaluator. No credentials were obtained or used.

NOT TESTED: official syntax/test validation and policy preview; authoritative inventory completeness/freshness; official wildcard-versus-explicit ICMP protocol equivalence and port-zero acceptance; live denied-peer access; live HTTPS 9443 narration. Native port availability is a separate acceptance gate and does not establish tailnet authorization. Recheck current listener and Serve state immediately before any later deployment; preserve 443 and 8443 throughout.

The minimum next step is an authenticated, read-only complete tailnet device/approved-route inventory and policy freshness check, followed by an owner-reviewed choice: maintain an explicit destination inventory or authorize another carefully scoped policy design. Then submit the private candidate and tests to Tailscale's official non-applying validation and preview operations through an already authorized administrator context. Do not save the policy or start the route on the strength of the offline checks. Require official positive FORGE and negative other-peer results, compare access to all existing destinations/services, and resolve the protocol-equivalence question first. Keep a current policy export as rollback evidence. Policy application remains a separate action owned by the coordinator.

Official references reviewed:

- [Grants syntax](https://tailscale.com/docs/reference/syntax/grants): wildcard destination scope, explicit protocol/port selectors.
- [Policy syntax and tests](https://tailscale.com/docs/reference/syntax/policy-file): additive permissions and policy tests.
- [IP sets](https://tailscale.com/docs/features/tailnet-policy-file/ip-sets): ordered add/remove ranges; wildcard membership is not a documented target.
- [Trust credentials](https://tailscale.com/docs/reference/trust-credentials) and [official client implementation](https://github.com/tailscale/tailscale/blob/main/client/tailscale/acl.go): distinct ACL validate/preview endpoints. No private policy was sent to them.

Ponytail FULL applied: reuse the existing policy and protected private evidence; no new network reader, execution mechanism, dependency or policy-management service. The diff review found no private identity/address in this sanitized report. Official evaluation and complete access preservation remain blocked as described above.
