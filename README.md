# Can We Build This: format teardown and replication plan

This repo holds the research for building an Instagram account in the same format as [@canwebuildthis](https://instagram.com/canwebuildthis). There is no code here, only notes, source material, and production guides.

## Status

The cloud environment that does this research cannot reach instagram.com. Its network policy only allows GitHub and package registries. The analysis of the account's own videos is waiting on one of these:

- **Upload the reels** to [`source/videos/`](source/videos/) and screenshots to [`source/screenshots/`](source/screenshots/). This is the most reliable route.
- **Open network access** for the environment. Instagram often blocks logged-out downloads from cloud servers, so this may still fail.

## Layout

| Path | What it holds |
|---|---|
| `source/videos/` | The account's reels, as downloaded `.mp4` files |
| `source/screenshots/` | Profile, grid with view counts, captions, comments |
| `analysis/` | The research and teardown documents |
