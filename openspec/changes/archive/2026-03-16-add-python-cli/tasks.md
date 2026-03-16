## 1. CLI foundation

- [x] 1.1 Add the CLI entrypoint to package metadata and create the base CLI module layout.
- [x] 1.2 Implement global option parsing for API key, base URL, timeout, logging, default user, JSON mode, and config/env resolution precedence.
- [x] 1.3 Implement shared client-factory helpers that instantiate the correct sync SDK client for each command group.
- [x] 1.4 Implement shared stdout/stderr rendering helpers for blocking JSON output, human-readable summaries, and non-zero exit handling.
- [x] 1.5 Implement shared parsers for `--input key=value`, `--inputs-json`, typed JSON value flags, and common identifier validation.

## 2. Core app, file, and schema-aware commands

- [x] 2.1 Implement `app` commands for info, site info, parameters/inspect, meta, site config read/update, and API token list/create/delete.
- [x] 2.2 Implement `files upload` and `files preview` commands and shared file-opening helpers for local upload flows.
- [x] 2.3 Implement `message feedback`, `audio-to-text`, and `text-to-audio` commands with explicit output contracts.
- [x] 2.4 Add schema-inspection normalization so `app inspect --json` exposes app input fields and file-upload capabilities consistently.

## 3. Completion, chat, and workflow commands

- [x] 3.1 Implement `completion send` with blocking/streaming response modes, structured inputs, and file attachment support.
- [x] 3.2 Implement `chat send` with explicit `--conversation-id`, custom inputs, local attach upload-then-send flow, and streaming output.
- [x] 3.3 Implement chat helper commands for suggestions, task stop, conversation list/messages, rename/delete conversation, annotations, and conversation variables.
- [x] 3.4 Implement workflow commands for run, run-specific, stop, result, logs, draft read/update, publish, and run history.

## 4. Workspace and knowledge-base commands

- [x] 4.1 Implement `workspace` commands for model discovery, provider model listing, credential validation, and file info/download-url/delete.
- [x] 4.2 Implement `kb dataset` commands for create, list, get, update, delete, template create, duplicate, and batch document status updates.
- [x] 4.3 Implement `kb document` commands for text/file create and update, list, delete, and indexing status with extra JSON payload support.
- [x] 4.4 Implement `kb segment`, `kb metadata`, `kb tag`, and `kb pipeline` command groups covering the remaining knowledge-base endpoints.

## 5. Documentation, parity, and release readiness

- [x] 5.1 Add tests for config precedence, input parsing, exit codes, and JSON output contracts.
- [x] 5.2 Add command tests for representative happy paths and failure cases across app, chat, workflow, workspace, and knowledge-base groups.
- [x] 5.3 Add parity coverage that asserts every public sync SDK method in scope has a documented CLI command mapping or an explicit canonical-command note.
- [x] 5.4 Update README and examples with installation guidance, two-round chat usage, custom inputs, file attachments, and representative knowledge-base/workflow commands.
- [x] 5.5 Verify package installation and CLI help output in a clean environment before release.
