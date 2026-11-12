# Security boundary

Only reviewed default-branch code may coordinate durable state. Pull request CI has contents-read permission and no publishing credentials. Actions are pinned to immutable upstream revisions. State writes are serialized and fast-forward only. External text is data, not an instruction source; network reads are HTTPS with a fixed host allowlist and bounded sizes/timeouts. Do not allow arbitrary media URL fetches or source-derived shell commands.

This repository and workflow artifacts are public. Never store tokens, passwords, OAuth clients, private blog source, personal mailbox content or raw videos here. No fork-triggered elevated jobs, `pull_request_target`, credential logging, paid infrastructure, or hidden alternate upload path. Upload/subscription OAuth and email are not enabled by bootstrap.

Stop switch: `PYTHONPATH=src python -m youtube_ops.cli pause` through the trusted manual coordination workflow. A stop blocks new publication; inspect any existing uncertain intent before deciding what to do next.
