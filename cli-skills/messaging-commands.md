# Messaging Commands

Use this file for application-facing commands: app metadata, file upload, completion, chat, audio, and workflow operations.

## Scope

- Root standalone commands:
  `message-feedback`, `audio-to-text`, `text-to-audio`
- Command groups:
  `app`, `files`, `completion`, `chat`, `workflow`

## Minimum Commands For Common Chatflow Tasks

- One-turn chat:
  `dify --json chat send --user "$DIFY_USER" --response-mode blocking --query "<message>"`
- Two-turn chat:
  run `chat send` once, extract `conversation_id` from the JSON response, then call `chat send` again with `--conversation-id`
- Upload then chat:
  run `files upload`, extract the upload ID, then call `chat send --file-ref document=<file_id>`
- Stop reading this file once you have the command shape you need.

## Root Standalone Commands

- `message-feedback`
  Purpose: send feedback for a prior message
  Key flags: `--message-id`, `--rating`, optional `--user`
- `audio-to-text`
  Purpose: transcribe an audio file through the chat client
  Key flags: `--path`, optional `--user`
- `text-to-audio`
  Purpose: synthesize audio from text
  Key flags: `--text`, optional `--user`, `--streaming`, `--output`
  Note: decide whether you need output metadata or written audio before invoking

## File Object Rules For Chat And Completion

- Valid `transfer_method` values are exactly `local_file` and `remote_url`.
- `--attach [type=]path`
  uploads a local path, then sends the file as `transfer_method: "local_file"` with `upload_file_id`.
- `--file-ref type=file_id`
  reuses an uploaded file and sends `transfer_method: "local_file"`.
- `--remote-file-url type=url`
  sends `transfer_method: "remote_url"` with a direct URL.
- Common CLI file `type` values are `document`, `image`, `audio`, and `video`.
- For text files or general attachments, prefer `document=...` when you need the type to be explicit.

## App Commands

- `app info`
  Purpose: fetch basic app information
- `app site-info`
  Purpose: fetch public site/app-site metadata
- `app parameters`
  Purpose: fetch raw application parameters
  Key flags: optional `--user`
- `app inspect`
  Purpose: fetch raw app parameters plus normalized input/file-upload hints
  Key flags: optional `--user`
  Use when: custom app inputs are unknown
- `app meta`
  Purpose: fetch app metadata
- `app site-config get`
  Purpose: read site configuration
  Key flags: `--app-id`
- `app site-config update`
  Purpose: update site configuration
  Key flags: `--app-id`, `--config-json`
- `app api-tokens list`
  Purpose: list app API tokens
  Key flags: `--app-id`
- `app api-tokens create`
  Purpose: create a new app API token
  Key flags: `--app-id`, `--name`, optional `--description`
- `app api-tokens delete`
  Purpose: delete an app API token
  Key flags: `--app-id`, `--token-id`

## File Commands

- `files upload`
  Purpose: upload a local file for later chat or completion use
  Key flags: `--path`, optional `--user`
- `files preview`
  Purpose: fetch a preview for an uploaded file
  Key flags: `--file-id`

## Completion Commands

- `completion send`
  Purpose: create a completion request
  Key flags: optional `--user`, repeated `--input`, `--inputs-json`, `--response-mode`, `--attach`, `--file-ref`, `--remote-file-url`
  Notes:
  - Use `--inputs-json` for typed values.
  - Keep file payloads in attachment flags, not inside normal inputs.
  - Use `--response-mode streaming` if you want event streaming instead of one final response.

## Chat Commands

- `chat send`
  Purpose: create a chat message
  Key flags: `--query`, optional `--user`, `--conversation-id`, repeated `--input`, `--inputs-json`, `--response-mode`, `--attach`, `--file-ref`, `--remote-file-url`
  Notes:
  - Preserve `conversation_id` from a previous response for multi-turn chat.
  - `--attach` uploads a local file before sending.
  - `--file-ref type=file_id` reuses an uploaded file ID and maps to `transfer_method: "local_file"`.
  - Use `document=<file_id>` for generic documents or text files when the file type needs to be explicit.
- `chat suggested`
  Purpose: fetch suggested follow-up prompts
  Key flags: `--message-id`, optional `--user`
- `chat stop`
  Purpose: stop a running chat task
  Key flags: `--task-id`, optional `--user`
- `chat conversations`
  Purpose: list conversations
  Key flags: optional `--user`, `--last-id`, `--limit`, `--pinned`
- `chat messages`
  Purpose: fetch messages for a conversation
  Key flags: `--conversation-id`, optional `--user`, `--first-id`, `--limit`
- `chat rename-conversation`
  Purpose: rename a conversation
  Key flags: `--conversation-id`, `--name`, optional `--user`, `--auto-generate`
- `chat delete-conversation`
  Purpose: delete a conversation
  Key flags: `--conversation-id`, optional `--user`
- `chat annotation-reply-action`
  Purpose: trigger an annotation reply action/job
  Key flags: `--action`, `--score-threshold`, `--embedding-provider-name`, `--embedding-model-name`
- `chat annotation-reply-status`
  Purpose: inspect annotation reply job status
  Key flags: `--action`, `--job-id`
- `chat annotations list|create|update|delete`
  Purpose: manage chat annotations
  Common IDs: `--annotation-id` for update/delete
- `chat variables list|update`
  Purpose: manage conversation variables
  Common IDs: `--conversation-id`, `--variable-id`
  Notes:
  - `chat variables update` requires `--value-json`.
  - Use typed JSON values when updating a conversation variable.

## Workflow Commands

- `workflow run`
  Purpose: run the default workflow entrypoint
  Key flags: optional `--user`, repeated `--input`, `--inputs-json`, `--response-mode`
- `workflow run-specific`
  Purpose: run a specific workflow by identifier
  Key flags: `--workflow-id`, optional `--user`, repeated `--input`, `--inputs-json`, `--response-mode`
- `workflow stop`
  Purpose: stop a running workflow task
  Key flags: `--task-id`, optional `--user`
- `workflow result`
  Purpose: fetch a workflow result
  Key flags: `--workflow-run-id`
- `workflow logs`
  Purpose: fetch workflow logs
  Key flags: optional `--keyword`, `--status`, `--page`, `--limit`
- `workflow publish`
  Purpose: publish a workflow
  Key flags: `--app-id`
- `workflow history`
  Purpose: fetch workflow run history
  Key flags: `--app-id`, optional `--page`, `--limit`, `--status`
- `workflow draft get|update`
  Purpose: read or update a workflow draft
  Key flags: `--app-id`, plus `--workflow-json` for update

## Agent Notes

- For chat and completion, inspect only if the app has unknown custom fields, file constraints, or unclear payload requirements.
- For multi-turn chat, capture both `conversation_id` and `message_id` from the first blocking response.
- For file-enabled app flows, prefer `files upload` plus `--file-ref` when you will reuse the same upload across multiple requests.
- In JSON mode, streaming chat or workflow calls return line-delimited JSON events rather than a final pretty response.
- Avoid `dify --help`, `app inspect`, and `app info` unless they change the next command you plan to run.

## Coverage

- OpenSpec capability:
  `python-cli-messaging`
