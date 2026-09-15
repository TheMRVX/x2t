# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-09-16

### Added
- Direct authenticated Twitter GraphQL extraction backend (`TwitterGraphQLBackend`) integrating `TweetResultByRestId` and `TweetDetail` endpoints.
- Support for session authentication binding (`auth_token` and `ct0`) across both single-tweet (`XMediaExtractor`) and profile (`ProfileExtractor`) extraction pipelines.
- Additional public fallback resolver endpoints (`fixupx`, `twittpr`) within `FxTwitterBackend`.
- Unit test suite for Twitter GraphQL backend payload parsing and tombstone detection (`tests/test_graphql_backend.py`).
- Automated source distribution (`.tar.gz`) and wheel (`.whl`) package builds for release artifacts.

### Changed
- Re-architected `XMediaExtractor` resolution cascade to prioritize authenticated GraphQL requests.
- Updated `docker-compose.yml` to include hot-reload volume mounts for `/app/x2t`.

### Fixed
- Resolved false-positive `NO_MEDIA_FOUND` errors caused by `TweetTombstone` responses from the Syndication API on age-restricted or login-required tweets.
- Fixed session token synchronization in `/set_cookie` administrative command to update single-tweet extractor state immediately upon configuration.

## [1.0.0] - 2026-09-01

### Added
- Initial production release of `x2t`.
- Multi-media extraction engine supporting carousels, 1080p/4K MP4 videos, and animated GIFs.
- Public fallback resolver integration via `FxTwitter` and `SyndicationBackend`.
- Profile timeline downloader with interactive filtering options and cursor-based pagination.
- Telegram Bot service supporting standard Bot API and MTProto direct upload modes (up to 2 GB).
- Persistent SQLite database with WAL mode and anti-flood throttling middleware.
- Multi-architecture container deployment configurations for Docker and Docker Compose.
