# KnowledgeNetwork

Rights-safe video operations for Powered By Oxieg3n. This public repository contains software and small public metadata only. It does not modify the separate website repository.

## Current implementation

- Four durable queues: fresh source uploads, daily recap, published-blog adaptations, historical top-ten research.
- 150 watchlist entries (121 unique names); ten channels initially verified with official identity evidence.
- Bounded official RSS discovery, optional YouTube Data API uploads-playlist reconciliation and archival ranking, live public blog sync.
- Versioned JSON state with single-writer workflow concurrency and optimistic conflict rejection.
- Local original-graphics/Piper renderer, FFmpeg QC, publication gates and recovery tests.
- Public operational reports and pending alert outbox. No email is claimed sent.

**Not yet fully autonomous:** official upload/subscription OAuth, an approved persistent render host, email route, finished editorial scripts and exact-render human-quality review remain required. Browser Studio sign-in is not API authorization. Production publication is paused by default. No video has been published by this software.

## Development

Python 3.11+; standard library only for metadata/testing. Optional rendering dependencies are pinned in `requirements-render.txt`.

```sh
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m youtube_ops.cli seed
PYTHONPATH=src python -m youtube_ops.cli monitor
PYTHONPATH=src python -m youtube_ops.cli blog-sync
PYTHONPATH=src python -m youtube_ops.cli report
```

The hosted Actions workflow runs short software validation and low-burden metadata coordination only. It never renders video, uploads videos, sends mail or subscribes to channels. See [operations](OPERATIONS.md), [security](SECURITY.md) and [rendering](docs/rendering.md).
