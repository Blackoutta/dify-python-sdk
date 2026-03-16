## Why

The SDK already exposes a broad Dify API surface, but agentic and shell-driven users still need to write Python code for every operation. A first-party CLI would make the SDK usable in automation pipelines, local tooling, and multi-step agent workflows while keeping the command contract aligned with the existing Python client.

## What Changes

- Add a Python-distributed CLI entrypoint to the package and document installation via `pipx`, `uv tool`, and local editable installs.
- Define a schema-aware command model that can inspect app parameters, accept structured `inputs`, upload or attach files, preserve explicit `conversation_id`, and emit stable machine-readable JSON.
- Cover the current public sync API surface with CLI command groups for base/app operations, chat/completion/workflow operations, workspace/file operations, and knowledge-base operations.
- Define shared CLI behavior for config resolution, authentication, request shaping, response formatting, streaming, exit codes, and error presentation.
- Add test coverage for command parsing, API-to-command mapping, JSON output contracts, and representative end-to-end flows across each API family.

## Capabilities

### New Capabilities
- `python-cli-core`: CLI installation, command discovery, global options, config/env precedence, schema inspection, structured input parsing, output formatting, and error/exit-code behavior.
- `python-cli-messaging`: CLI commands for base app operations, file upload, completion, chat, conversation helpers, message feedback, media conversion, and workflow execution/logging.
- `python-cli-management`: CLI commands for workspace/model management and knowledge-base dataset, document, segment, metadata, tag, and pipeline operations.

### Modified Capabilities

None.

## Impact

- Affects packaging metadata, distribution docs, and the public surface of the `dify-client` package by adding a supported CLI entrypoint.
- Adds a CLI implementation module, shared request/formatting helpers, and command tests that map onto the existing sync client classes.
- Requires clear documentation of how CLI commands map to `DifyClient`, `ChatClient`, `CompletionClient`, `WorkflowClient`, `WorkspaceClient`, and `KnowledgeBaseClient`.
