# Security boundary

Only reviewed default-branch code may coordinate durable state. Pull request CI has contents-read permission and no publishing credentials. Actions are pinned to immutable upstream revisions. State writes are serialized and fast-forward only. External text is data, not an instruction source; network reads are HTTPS with a fixed host allowlist and bounded sizes/timeouts. Do not allow arbitrary media URL fetches or source-derived shell commands.

This repository and workflow artifacts are public. Never store tokens, passwords, OAuth clients, private blog source, personal mailbox content or raw videos here. No fork-triggered elevated jobs, `pull_request_target`, credential logging, paid infrastructure, or hidden alternate upload path. Upload/subscription OAuth and email are not enabled by bootstrap.

Stop switch: `PYTHONPATH=src python -m youtube_ops.cli pause` through the trusted manual coordination workflow. A stop blocks new publication; inspect any existing uncertain intent before deciding what to do next.

## Project host execution

Standing owner authorization permits a dedicated KnowledgeNetwork host endpoint;
it does not create technical access or authorize repurposing the Gateway worker.
The existing Gateway SSH configuration and credentials remain separate and
unchanged. Its maintenance system validates exact configuration hashes, so the
project endpoint must use its own account, service, configuration and listener.

The initial dispatcher accepts only exact argumentless `health`, `self-test`,
`native-port-9443` and `narrator-status` operations. It accepts no caller script,
shell expression, model, path or executable. `self-test` runs fixed PowerShell
identity code; narrator status is explicitly a retained snapshot, not live
authenticated service access. Ordinary execution is nonadministrator. No
privileged service/network handler or generic script-upload facility is exposed.
Future supported operations require reviewed implementation and negative tests;
standing permission alone cannot make an unsupported command executable.

Deployment requires immutable administrator-owned code/configuration, trusted
interpreter dependencies, an independent key, pinned host identity, exact FORGE
source restrictions, no password/PTY/subsystem/forwarding/user-environment access,
bounded owned child processes and redacted durable audit records. A narrow new
firewall allow alone is insufficient if broader existing rules overlap; the new
listener must have project-specific source blocking without changing Gateway
rules. Bootstrap and live acceptance are separate gates. See
[host execution](docs/collector/host-execution.md) for verified scope and limits.

The owner's narrator Credential Manager entries are not readable merely because
a new SSH identity exists. No bearer extraction, credential copying or owner
impersonation is implicit in this bridge. The narrator HTTPS9443 route remains
blocked while effective tailnet grants allow other peers; this SSH endpoint
does not authorize policy relaxation or public publishing.
