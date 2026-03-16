## ADDED Requirements

### Requirement: Base app and file commands map to DifyClient operations
The CLI SHALL provide commands for `message_feedback`, `get_application_parameters`, `file_upload`, `text_to_audio`, `get_meta`, `get_app_info`, `get_app_site_info`, `get_file_preview`, `get_app_site_config`, `update_app_site_config`, `get_app_api_tokens`, `create_app_api_token`, and `delete_app_api_token`.

#### Scenario: App metadata commands preserve identifiers and payloads
- **WHEN** a user requests app info, site info, site config, API tokens, or metadata in JSON mode
- **THEN** the CLI returns the corresponding response payload without renaming required API identifiers

#### Scenario: File upload supports local file paths
- **WHEN** a user runs the file upload command with a local path and user identifier
- **THEN** the CLI uploads the file through the SDK, returns the uploaded file ID in JSON mode, and can reuse that ID in later chat or completion requests

### Requirement: Completion commands support structured inputs and attachments
The CLI SHALL expose a completion send command that maps to `CompletionClient.create_completion_message`, supports `blocking` and `streaming` response modes, accepts structured `inputs`, and supports file payloads compatible with Dify vision-style requests.

#### Scenario: Completion send with blocking mode
- **WHEN** a user sends a completion request with inputs and blocking mode
- **THEN** the CLI returns the full completion response as JSON or a concise human summary

#### Scenario: Completion send with attached file
- **WHEN** a user provides an uploaded file ID or inline attachment path for a completion request
- **THEN** the CLI shapes the request into the `files` payload expected by the SDK and sends the non-file custom fields through `inputs`

### Requirement: Chat commands support multi-turn explicit conversations
The CLI SHALL expose chat send and helper commands that map to `create_chat_message`, `get_suggested`, `stop_message`, `get_conversations`, `get_conversation_messages`, `rename_conversation`, and `delete_conversation`, and the send command MUST accept explicit `conversation_id`.

#### Scenario: First-round chat returns conversation identifiers
- **WHEN** a user sends a first chat message in blocking JSON mode
- **THEN** the response includes the API-provided `conversation_id`, `message_id`, and any task metadata needed for follow-up calls

#### Scenario: Second-round chat reuses explicit conversation state
- **WHEN** a user sends a second chat message with `--conversation-id`
- **THEN** the CLI passes that identifier unchanged to the SDK rather than creating hidden local session state

### Requirement: Chat commands support custom inputs and file fields
The chat send command SHALL accept both custom scalar inputs and file-oriented inputs, and file handling MUST remain distinct from normal `inputs`.

#### Scenario: Custom app fields are sent alongside query text
- **WHEN** a user provides `--query` and one or more custom input fields
- **THEN** the CLI sends the message text as `query` and the additional fields as the `inputs` object

#### Scenario: Local attachment triggers upload-then-send flow
- **WHEN** a user passes a local file path through an attachment flag on chat send
- **THEN** the CLI uploads the file first, transforms the result into a Dify-compatible `files` entry, and then sends the chat request

### Requirement: Audio conversion and message feedback are first-class commands
The CLI SHALL expose commands for `audio_to_text`, `text_to_audio`, and `message_feedback` with stable input/output contracts suitable for shell scripting.

#### Scenario: Audio-to-text returns transcription payload
- **WHEN** a user submits an audio file for transcription in JSON mode
- **THEN** the CLI uploads the file through the SDK and returns the transcription response without mixing binary data into stdout

#### Scenario: Text-to-audio handles streaming and blocking behavior explicitly
- **WHEN** a user requests text-to-audio conversion
- **THEN** the CLI requires an explicit output handling mode and writes either response metadata or audio output according to the command contract

### Requirement: Annotation and conversation-variable commands are canonicalized
The CLI SHALL expose one canonical command for each annotation and conversation-variable endpoint, covering the behavior of both canonical and duplicate helper methods in `ChatClient`.

#### Scenario: Annotation list maps duplicate SDK helpers to one command
- **WHEN** the SDK provides multiple list or update helpers for annotations
- **THEN** the CLI exposes a single list command and a single update command with pagination flags rather than duplicate aliases

#### Scenario: Conversation variable update preserves arbitrary JSON values
- **WHEN** a user updates a conversation variable with a typed JSON value
- **THEN** the CLI sends the value without coercing it to a string

### Requirement: Workflow commands cover execution and administration
The CLI SHALL provide commands for `run`, `stop`, `get_result`, `get_workflow_logs`, `run_specific_workflow`, `get_workflow_draft`, `update_workflow_draft`, `publish_workflow`, and `get_workflow_run_history`.

#### Scenario: Workflow run supports blocking and streaming modes
- **WHEN** a user runs a workflow command with a chosen response mode
- **THEN** the CLI maps that mode directly to the SDK request and formats the response according to the global output contract

#### Scenario: Workflow admin commands accept app-scoped identifiers
- **WHEN** a user requests workflow draft, publish, or run history operations for a specific app
- **THEN** the CLI requires the relevant app or workflow identifier and dispatches the matching SDK method without hidden defaults
