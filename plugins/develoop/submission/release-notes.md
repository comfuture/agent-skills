# Develoop 0.1.3 — Behavior-preserving State Cleanup

Develoop 0.1.3 adds `cleanup-slops`, a cleanup workflow for implicit state
machines across an entire repository or a specified pull request.

Highlights:

- Starts from “find all of the implicit state machines in my app” and traces
  state ownership, reachable combinations, transitions, consumers, and invariants.
- Removes redundant sources of truth while preserving independent state axes,
  async request ownership, public APIs, and persisted representations.
- Establishes baseline behavior and focused regression evidence before editing,
  with decision examples for essential and unnecessary state.
- Keeps PR cleanup within the implementation and its relevant dependencies,
  reporting preserved or deferred candidates and uninspected areas.
- Preserves category, capabilities, public support links, starter prompts, and
  release notes in the OpenAI submission ZIP.
- Records the UTC time and full head before marking a draft ready, and reuses
  existing trigger evidence when a PR is already ready.
- Retains the head-aware, causally bounded automated-review guidance from 0.1.2.

Reviewer notes:

- Submission type: Skills only
- Version: 0.1.3
- Publisher: Changkyun Kim
- Category: Developer Tools
- Support: https://develoop.comfuture.chatgpt.site/support
- Validation: 36 repository regression tests, seven website route tests, and
  independent repository-wide and PR-scoped cleanup exercises
- License: MIT AND CC-BY-NC-SA-4.0
