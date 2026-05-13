# Docs

This directory is organized by document lifecycle.

- `road.md` is the agent- and human-readable project roadmap. Use it for durable direction, sequencing, and major milestones.
- `todo.md` is a human-controlled sketchpad. It can stay rough, current, and personal.
- `specs/` contains authoritative simulator behavior references. `specs/card_specifics.md` is the source of truth for card-specific behavior.
- `workstreams/` contains repeatable implementation workflows. Use `workstreams/card_specific.md` for card bucket work.
- `notes/` contains compact ContextNotes that mirror selected source and test files. Agents should read matching notes before editing `mtg_sim/`.
- `planning/` contains active planning documents and phased implementation prompts.
- `prompts/` contains reusable prompt material. `prompts/archive/` is historical; paths and instructions there may be stale.
- `logs/` contains append-only or session-derived logs, including introspection notes.
- `samples/` contains example JSON shapes and fixtures used by docs or prompts.
- `backlog/` contains backlog formatting and process instructions.
