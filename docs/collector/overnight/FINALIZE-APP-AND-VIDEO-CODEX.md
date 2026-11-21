# V9 Finalize Collector: standing project authorization and end-to-end video acceptance

**Owner directive: November 20, 2026.** This is a current execution handoff for the existing FORGE Codex coordinator. Apply it alongside AGENTS.md and the latest HANDOFF.md. Historical recovery notes remain evidence, not instructions to redo old work.

## Outcome first

Complete **The Knowledge Network Collector** as a usable Windows application and deliver **one genuinely narrated, fully editable 50-second portrait video** (native OpenShot project plus locally playable MP4) with the approved dynamic intro and unchanged approved outro. Demonstrate the real FORGE-to-BLACKHAT-BASE narration path and preserve owner review gates. Do not merely produce another plan, mock, synthetic narration acceptance, or code-only demo.

Continue the EXISTING feature branch and worktrees. At this directive, the last verified head was 305a7129d91aca0a686420114c014b6d58d9a9fa and PR #20 was draft, unmerged and conflicting with main. **Recheck live HEAD and status before work.** Never reset, force-push or auto-merge. Do not modify the separate poweredby repository. Publication remains **PAUSED**.

## Standing project-scoped owner authorization

The owner controls FORGE and BLACKHAT-BASE and **explicitly authorizes Codex to execute all necessary project-related development, PowerShell/Python, diagnostics, local inference, data/permission/service/firewall configuration, secure route setup, app installation and test commands without asking for repeated command-by-command consent**.

BLACKHAT-BASE and its local drives are the owner's accepted development environment. The owner accepts the documented inherited Authenticated Users Modify/DELETE permissions on the existing D: directory tree **as a local development risk**. Do not treat that fact alone as a veto on all project progress, or require a systemwide permission redesign for a working app.

**This is an authorization and scope decision, not a claim of cryptographic integrity.** Verify actual Windows access, administrator elevation where legitimately needed, process and file identity for sensitive operations, service state and occupied ports. For new privileged or unattended code, prefer a protected ProgramData execution/configuration location, least privilege and reviewed fixed operations. Do **not** lie to an existing trust checker, bypass another process's authentication, execute user-writable code as SYSTEM, or assume a running SQLite database can safely be moved or replaced. If old V2 repair requires proof that is unavailable, **defer that repair and choose an independently safe owner-context implementation**. Do not retry the held V2 procedure.

Standing permission includes project-specific firewall allow/block rules, narrow Windows ACL or task/service permission changes, dedicated project user/service setup, loopback listener on 127.0.0.1:39110, and a private Tailscale HTTPS 9443 route **only if** the exact target/source and effective restrictions are freshly verified, unrelated access remains intact, and a precise rollback is recorded. Prefer existing approved infrastructure over another framework. Existing v5 tailnet policy was owner-approved, applied and post-verified in V9-TAILNET-REMEDIATION.md; reuse that evidence, then check for drift before opening 9443. Preserve existing 443/8443 Serve routes, Universal Gateway, separate SSH worker and other apps. Do not enable Funnel or general public ingress. Any broader policy change that would alter unrelated access is outside this standing authorization.

Use the already accepted FORGE-to-host restricted SSH bridge **within its actual fixed capabilities**. A prompt cannot turn its dispatcher into an arbitrary remote shell. Where an authorized host operation is unavailable through that channel, implement a reviewed, fixed, authenticated project handler or owner-context task, with tests; if first-time elevation cannot be achieved through a legitimate existing channel, return **one minimal, verified owner-side bootstrap step**, then continue without repeated prompts. Never request or print plaintext credentials; provision secrets through scoped Credential Manager/hidden prompts.

No permission is granted to erase project history/data, overwrite backups, change unrelated host settings, use third-party voices without rights, distribute unreviewed host model dependencies, pay for services, make public uploads, merge PR #20, or reboot machines without a specifically reviewed operational need and owner's separate reboot approval.

## Reuse completed acceptance: do not rework it

- Collector installed worker, medium-integrity authenticated named pipe and Assistant-context manual health passed. Stable queue/worker identity and database preservation are documented.
- Original direct VoxCPM2 2.0.3 narrator passed one real CUDA/bfloat16 3.04-second diagnostic and owner listening approval. Diagnostic WAV digest: 1083cd235598378fe4c7fc0556dcba1f9d3a9334b48620d522c2e826134dc6b7. The approved reference digest is 050db3aeca148b98dd2edbcdf77abcb12b7ebc1debb344879e81af6e49b7fe44. Model revision 7936080b41163874f38610f46f438e2c0757f9fd.
- Keep canonical narrator script at D:/tools/audio/voices/Oxiegen-Narrator/narrate.ps1 and its exact reference, CFG2.0, ten steps, no denoiser/optimization, local-files-only and compile-disabled settings. Never resurrect VoiceStudio as a service dependency.
- Owner's private synthetic voice authorization and local-use review exist. Retain evidence and notices; do not confuse private use and generated WAV rights with redistribution of bundled NVIDIA/LGPL/model components.
- Approved portrait and landscape 7.8-second outros, the exact emblem PNG, and the 4-second preview were already recovered and hash-verified in the private FORGE evidence. Reuse documented paths and SHA-256 in V9-CLIENT-VIDEO-PREPARATION.md. The 4-second preview is **not** the 1.6-second production intro.
- Original technical 50-second .osp and MP4 exist. Preserve them, but do not call them a full narrated/branded acceptance.
- v5 Tailscale policy was applied and post-verified for current inventoried peers; the route itself is not thereby deployed. Restricted host SSH diagnostics passed. Do not rerun costly inventory, model smoke or host bootstrap without new evidence.

## Implementation order: execute, don't only investigate

### A. Pick the shortest safe route to real narration

1. Confirm whether the existing restricted loopback narrator API is already live; determine actual listener, credential, manifest, spool, jobs and task state without disturbing active records.
2. If the old controller is blocked by unsafe ledger ancestry, **leave it running and held**; do not fix it by disabling validation or stopping its SQLite process blindly. Prefer an independent, owner-context, separately journaled narrator API instance using already reviewed host/client code and a fresh private data root, after checking that port, spool, credential target and process ownership cannot collide. If an additional worker is unnecessary, reuse the original supported API under its actual owning identity.
3. Validate existing reviewed manifest and scoped Credential Manager bearer under the correct identity; do not use the nonadmin SSH account to read the owner's secret.
4. Confirm Tailscale Serve 9443 has no collision, effective FORGE-only reachability, service loopback bind, normal TLS hostname/certificate validation and rejection of unauthorized peers. Implement only the approved scoped change with backups.
5. From FORGE, run the existing real authenticated client: health/status, one new short narration job with a durable idempotency key and captured text, one actual downloaded WAV, checked PCM/duration/segment digest and exact provenance. Unknown POST/response outcomes must recover the **same** job and must not silently retry under another ID.
6. Call this REMOTE_NARRATION_PASS only after the real request/receipt, not after file copy or synthetic unit tests. If secure HTTPS setup cannot proceed, a genuinely generated WAV transferred via an approved private file channel can be used **temporarily** to continue editing, but is not proof of the API or final app acceptance.

### B. Build the actual editable video

1. Restart or create a fresh project-isolated supported OpenShot 4.1.1 session if the historical session is gone; verify the real GUI/native adapter and do not overwrite the preserved technical .osp.
2. Use an original evergreen tech topic suitable for a Knowledge Network demo and source/rights-safe visuals. Do not pretend current news facts are verified without research.
3. Author body narration to fit **1218 frames / 40.6 seconds** with measured audio, natural sentence/caption segments and retakes if needed. Do not stretch, truncate or speed the voice merely to force duration. Serialize GPU jobs.
4. Produce exactly **48 frames / 1.6 seconds** of the dynamic approved plasma intro using the exact emblem and video-specific title. Follow with exactly **1218 body frames**, then exactly **234 frames / 7.8 seconds** of the original approved portrait outro and unchanged spoken CTA. Total = **1500 frames / 50.0 seconds** at 30 fps, 1080x1920.
5. Include three visually distinct body scenes, two or more independent video/graphic layers, real titles/lower thirds, an animated effect, correctly timed captions, real Oxiegen-Narrator speech, separately ducked music and transitions. Keep media tracks editable in the native .osp. Use existing structured editor operations rather than inventing another timeline.
6. Save, reopen, make a real caption or graphic edit, save again, export that final revision, fully decode, check dimensions/fps/frame count/black frames/long silence/audio balance and inspect representative frames. Record owner listening as unreviewed until owner hears the **final** mix.
7. Deliver exact private project and MP4 paths, file hashes, screenshots and a simple local playback instruction. Do **not** upload the media to GitHub or YouTube.

### C. Finish the application and test it

1. Replace legacy destructive fixture cleanup safely, preserving the owner's archive-only policy. The old full CI suite was blocked by 110 deletion sites; make genuine code/fixture corrections instead of removing test assertions or disabling retention preflight. Ephemeral CI runner storage is not permanent archival; document its scope and retain required evidence appropriately.
2. Review PR #20's current main conflicts and resolve them with ordinary, reviewable feature-branch changes. Preserve latest main's independent approved files and workflow settings; no rebase/force-push/automatic merge.
3. Run focused tests, full supported regression, Windows worker and WPF tests, native editor checks and negative service/IPC/credential tests at their applicable scope. Keep skipped or unavailable tests explicit. Reuse existing receipts when unaffected.
4. Exercise a new clean, isolated installer install/upgrade/rollback only if technically isolated; don't overwrite the working installed Collector to claim an untested installer pass.
5. Demonstrate owner GUI interaction, Collector-to-editor job operations, installed CLI and at least one actual Dot/Assistant user-context manual workflow. Scheduled and reboot reliability are distinct later checks; do not mislabel manual PASS as scheduled PASS.
6. Use Ponytail FULL, UI/UX Pro Max and Taste where genuinely applicable. Fix observed problems; do not launch a gratuitous visual redesign.

## Archive-only retention

No automatic deletion. Archive verified obsolete project artifacts under:
- FORGE local repository: C:/Admin/Projects/KnowledgeNetwork/old
- FORGE private: C:/Admin/Projects/KnowledgeNetwork-Private/old
- BLACKHAT-BASE private project: D:/projects/knowledgenetwork/old, only where safely allowed.

Keep private credentials, live SQLite/sidecars, security/rollback evidence and original approved media in their protected live locations. Never move active files just because they are old. Verify hash, source/destination identity, permissions and receipts. If archive is blocked, leave files in place for owner cleanup later.

## Coordinator's stop/go rules

Work autonomously on all authorized tasks, including narrow app-specific firewall/permission/service changes. **Do not use a previously discovered ACL concern as a blanket veto** on an independent path that preserves actual integrity and data. Conversely, **do not claim trusted execution based only on the owner's risk acceptance** where a privileged process could load mutable code or another process might own a live ledger. Resolve the concrete issue with the minimum alternate design, then advance.

Stop only for unavailable OS credentials/technical access, an actual collision/uncertain process outcome, a documented material risk to unrelated services, unresolved required rights, or an action outside the above authorization. In that case finish all unaffected work and provide the smallest exact owner step. Don't ask permission again for steps expressly approved here.

Push only sanitized source/docs to the existing feature branch, update HANDOFF.md, and report **PASS, FAILED, BLOCKED, NOT TESTED** distinctly. Keep original backups, Gateway, policy, SSH pins, existing services and PR #20 draft. **PUBLICATION PAUSED.**

## Definition of done

A real, authenticated or properly isolated owner-host narration workflow; confirmed FORGE receipt; one native editable OpenShot Short with approved intro/outro, measured real voice and verified final 50-second export; working Collector desktop/service controls; meaningful CI and native checks; owner-reviewable local artifact and practical launch instructions. Separate unfinished features must be named, not hidden behind a generic PASS.

When a blocked historical controller prevents no independent work, mark that old recovery **DEFERRED** and proceed to finish the video and app.