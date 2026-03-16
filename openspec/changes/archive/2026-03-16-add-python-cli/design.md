## Context

The repository currently ships a Python SDK with synchronous client classes exported from `dify_client.__init__` and async counterparts used for parity tests. The public sync surface spans six client families: `DifyClient`, `CompletionClient`, `ChatClient`, `WorkflowClient`, `WorkspaceClient`, and `KnowledgeBaseClient`. There is no CLI entrypoint, no command parser, and no shared command/output contract for shell or agent use.

The CLI must be useful for both humans and automation. That creates a dual requirement: commands need to be discoverable and readable interactively, but they also need to be deterministic for agents. The design therefore needs a stable JSON contract, explicit state passing, and a command taxonomy that tracks the existing client APIs closely enough to avoid translation drift.

## Goals / Non-Goals

**Goals:**
- Add a first-party Python CLI distributed with the package and built on the existing sync client classes.
- Define a stable command hierarchy that covers the current public sync API surface.
- Make the CLI schema-aware where the API already exposes schema metadata, especially `user_input_form` and file-upload settings.
- Optimize for agentic use with explicit identifiers, JSON output, predictable exit codes, and non-interactive defaults.
- Keep API-to-command mapping straightforward enough that SDK changes can be reflected in the CLI without a separate translation layer.

**Non-Goals:**
- A native compiled binary distribution in v1.
- Wrapping the async-only internal client classes as separate CLI surfaces.
- Local session persistence that hides Dify `conversation_id` values by default.
- Interactive wizards, TUI flows, or credential storage beyond simple environment/config resolution.
- Inventing semantic abstractions that do not map back to existing SDK methods or Dify request shapes.

## Decisions

### 1. Build the CLI in Python with Typer and package it as a console script

The CLI will live in the same package and be exposed through `project.scripts` as a `dify` command. Typer is the preferred parser because it is already present in the lockfile, provides command-group ergonomics, and builds on Click without introducing a foreign runtime.

Alternatives considered:
- `argparse`: lower dependency cost, but weaker ergonomics for a large nested command surface.
- raw Click: viable, but Typer gives better typing and help generation for a spec-heavy CLI.
- Go/TypeScript: better binary story, but they would create a second implementation of the SDK contract before the command model has been validated.

### 2. Use the synchronous client classes as the only transport layer

The CLI will instantiate the existing sync clients and map commands directly onto public methods. Async clients remain library concerns and are not exposed as separate CLI modes. This keeps request semantics, retries, validation, and future compatibility anchored to the current SDK behavior.

Alternatives considered:
- Separate CLI-only HTTP client: would duplicate request behavior and drift from the SDK.
- Async CLI internals: unnecessary complexity for a command-driven process model.

### 3. Organize commands by resource domain, not by client class name

The root command will use a small number of top-level groups that reflect user tasks:
- `app`
- `files`
- `completion`
- `chat`
- `workflow`
- `workspace`
- `kb`

Shared/global flags live at the root. Commands map to public sync methods, but duplicated helper methods that hit the same endpoint (for example `list_annotations` and `list_annotations_with_pagination`) will produce one canonical CLI command.

Alternatives considered:
- A `client`-centric hierarchy mirroring class names exactly. Rejected because it is less intuitive and duplicates shared concerns.
- A single flat command list. Rejected because the knowledge-base surface is too large for discoverability.

### 4. Prefer explicit state and structured data over hidden magic

The CLI will accept:
- explicit `--conversation-id` for follow-up chat requests
- repeated `--input key=value` pairs for simple string fields
- `--inputs-json` for typed or nested data
- explicit file-oriented flags (`--attach`, `--remote-file-url`, `files upload`) instead of treating files as normal input fields

`--inputs-json` overrides repeated `--input` values when both are present. Repeated `--input` values are parsed as strings only. This avoids shell-side type inference ambiguity and gives agents a predictable contract.

Alternatives considered:
- Auto-typing scalar values from `--input`: convenient, but too ambiguous for agent use.
- Local session files that remember the last conversation automatically: helpful for humans, but too implicit for automation.

### 5. Make schema-awareness additive, not mandatory

The CLI will expose `app inspect` and use `get_application_parameters(user)` as the canonical discovery command. `chat send`, `completion send`, and `workflow run` accept raw inputs even when schema metadata is unavailable, but if inspection data exists the CLI will optionally validate required fields, highlight unknown fields, and normalize file-field guidance in error messages.

Alternatives considered:
- A pure thin wrapper with no schema awareness. Rejected because the API already exposes useful form metadata.
- Mandatory preflight inspection on every command. Rejected because it adds latency and couples commands to metadata availability.

### 6. Standardize output and error behavior for agentic consumption

All commands will support `--json` for stable machine-readable output. Default human mode may render concise summaries, but JSON mode must preserve raw response payloads plus minimal CLI metadata only when necessary. Non-zero exit codes are reserved for distinct classes: validation/config errors, authentication/authorization failures, API errors, transport/retry exhaustion, and unexpected internal failures.

Streaming commands (`chat send`, `completion send`, `workflow run`, pipeline run) will support:
- `--stream` / `--response-mode streaming` for line-delimited event output
- `--json` in blocking mode for full response objects
- an event-stream format in streaming mode that emits one JSON object per line without interleaved prose

Alternatives considered:
- Always pretty-printing JSON. Rejected because agents need compact stable output.
- Hiding HTTP/API failures behind generic messages. Rejected because automation needs diagnosable failures.

### 7. Cover the public sync API surface in phases, but define the full contract now

The spec will include the complete command taxonomy for the current sync API surface. Implementation will proceed in phases:
- Phase 1: core wiring, app/files/chat/completion/workflow happy paths
- Phase 2: workspace and knowledge-base coverage
- Phase 3: schema validation, streaming polish, docs/examples, and parity hardening

The contract is complete up front so later phases fill in implementation without revisiting command names or I/O shapes.

Alternatives considered:
- Spec only v1 commands and defer the rest. Rejected because the user explicitly asked for all APIs and a complete implementation spec.

## Risks / Trade-offs

- [Large command surface] → Mitigation: group by domain, define canonical commands only, and stage implementation in phases while keeping the published contract stable.
- [SDK/API drift] → Mitigation: map commands directly onto exported sync methods and add parity tests that assert each covered method has a documented command mapping.
- [Schema metadata inconsistency across Dify apps] → Mitigation: make validation advisory unless the API clearly marks a field as required; always allow raw JSON inputs.
- [Streaming output becomes hard to script] → Mitigation: enforce one-event-per-line JSON for streaming mode and no mixed human/log output on stdout.
- [Knowledge-base commands become unwieldy] → Mitigation: use nested `kb dataset`, `kb document`, `kb segment`, `kb metadata`, `kb tag`, and `kb pipeline` groups with consistent identifier flags.
- [Config precedence surprises users] → Mitigation: document and test a strict precedence order of CLI flag > environment variable > config file default.

## Migration Plan

1. Add the console-script entrypoint and CLI module without changing existing SDK imports.
2. Document installation and the core command families in the README.
3. Implement shared option parsing, client factory helpers, JSON rendering, and error handling.
4. Implement command groups in the order defined by the tasks plan.
5. Add command tests alongside existing client tests and verify the package still installs and imports as an SDK.
6. Release as a backward-compatible minor version because it adds functionality without changing the Python API.

Rollback is straightforward: remove the new CLI entrypoint and module while leaving the SDK untouched.

## Open Questions

No blocking open questions remain for the initial proposal. Optional future enhancements that are intentionally deferred include shell completion generation, persistent named profiles, and a local session helper layered on top of explicit `conversation_id`.
