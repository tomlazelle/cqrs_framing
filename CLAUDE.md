# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`cqrs-framing` is a small Python (>=3.10) library implementing CQRS plus domain events, inspired by .NET's CommandQuery.Framing. Source is in `src/cqrs_framing/` (src layout); tests are in `Tests/` (capital T). The only runtime dependency is `di-done-right`, imported as `di_container`.

## Commands

```bash
pip install -r requirements-dev.txt && pip install -e .   # setup
pytest Tests/                                             # all tests
pytest Tests/test_broker.py::test_name                    # single test
pytest Tests/ --cov=cqrs_framing                          # with coverage
ruff check src/cqrs_framing Tests examples                # lint
black --check src/cqrs_framing Tests examples             # format check (drop --check to fix)
mypy src/cqrs_framing                                     # types (disallow_untyped_defs is on)
```

CI (`.github/workflows/ci.yml`) runs exactly lint, black, mypy and pytest on Python 3.10–3.12, and publishes to PyPI on release. Line length is 88. Ruff ignores E501.

## Architecture

The flow is `Broker` → `HandlerRegistry` → handler, optionally wrapped in a `Pipeline`, with domain events dispatched afterward.

- **Sync and async are two parallel tracks everywhere.** `Handler[TReq, TRes]` has `execute(message)`. `AsyncHandler` has `async execute(message, cancellation_token)`. `HandlerRegistry` keeps separate `_sync` and `_async` maps, so the same request type can have one of each. `Broker` has `handle` / `handle_async`, and takes separate `sync_pipeline` / `async_pipeline`. Contexts are `HandlerContext` and `AsyncHandlerContext`. Any change to one track usually needs the matching change in the other.
- **Registry** ([registry.py](src/cqrs_framing/registry.py)) maps request type → handler type, and resolves handlers through a `DIContainer`. Sync vs. async is decided by `inspect.iscoroutinefunction(execute)`. `register()` fails fast with `InvalidHandlerSignatureError` if the handler doesn't subclass `Handler` / `AsyncHandler` or `execute` has the wrong signature (extra params must have defaults). Registering a second handler for the same request type and track raises `DuplicateHandlerError`. `register_instance()` skips DI construction.
- **Pipeline** ([pipeline.py](src/cqrs_framing/pipeline.py)) is async-only middleware: `async (ctx, next) -> result`, run in the order added. The broker's terminal step resolves and runs the handler, and records `success`, `exception` and `error_message` on the context. Middleware can short-circuit by setting `ctx.response` and `ctx.should_continue = False`. There are two layers: the broker-wide `sync_pipeline` / `async_pipeline`, and an optional per-handler pipeline passed as `pipeline=` to `register` / `register_instance` / `@handler`. Order is global → handler pipeline → `execute`; a sync handler pipeline also needs `asyncio.run`, so the running-loop guard applies to it too.
- **`Broker.handle` with a `sync_pipeline`** runs the async pipeline via `asyncio.run`, so it raises `RuntimeError` if called while an event loop is already running. Use `handle_async` from async code.
- **Domain events**: if a handler returns an `AggregateRoot` and the broker has a `DomainEventDispatcher`, the dispatcher drains `pending_events` (clearing them first) and publishes each to the `EventHub`. Aggregates record events with `_raise(...)`.
- **Events** ([events.py](src/cqrs_framing/events.py)): `Event[T]` supports `+=` / `-=` subscription and accepts sync or async handlers. Bound methods are held by `WeakMethod`, so subscribers can be garbage collected. `fail_fast` controls whether handler exceptions stop propagation. `EventHub` has one `Event` channel per event type, published with `publish` / `publish_async`.
- **Decorator registration** ([decorators.py](src/cqrs_framing/decorators.py)): `@handler(RequestType)` registers into a module-global registry that must first be set with `set_default_registry(...)`. Handlers must still inherit from the base classes.
- Public API is re-exported from [__init__.py](src/cqrs_framing/__init__.py). Add new public names there.

## Notes

- `di_container` has no type stubs; mypy is configured to ignore it (`# type: ignore[import-untyped]` at the import).
- Root-level docs (`README.md`, `QUICKSTART.md`, `DEPENDENCY_INJECTION.md`, `PROJECT_STRUCTURE.md`) describe usage; `examples/` has runnable samples that CI also lints.
