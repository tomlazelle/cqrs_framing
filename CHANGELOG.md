# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project aims to follow Semantic Versioning.

## [Unreleased]

## [0.2.0] - 2026-10-28

### Added

- Handler-specific pipelines: `HandlerRegistry.register(..., pipeline=)`,
  `register_instance(..., pipeline=)` and `@handler(..., pipeline=)`. They run
  inside the broker's global pipeline (global -> handler -> handler.execute).

## [0.1.1] - 2026-01-09

### Added

- Governance/compliance files: LICENSE, SECURITY.md, CONTRIBUTING.md
- CI workflow running tests, mypy, and minimal linting

### Changed

- Clarified sync/async runtime semantics (event loop requirements)
- Improved error messages for misuse of sync APIs in async contexts

## [0.1.0] - 2026-01-09

### Added

- Initial CQRS + domain events framework implementation
- Middleware pipeline support
- Dependency injection integration
- Core test suite
