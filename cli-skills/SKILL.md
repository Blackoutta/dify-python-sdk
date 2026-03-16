# Dify CLI Fast Path

Use this skill to execute the `dify` CLI with the fewest possible discovery steps.

## Default Behavior

- Treat this file as the fast path for common agent tasks.
- Prefer one direct CLI attempt over exploratory help calls when the needed flags are already shown below.
- Use explicit flags when the task already gives you credentials, base URL, or user identity. Otherwise rely on documented environment variables or config-file defaults.
- Do not run `dify --help`, `dify <group> --help`, `app inspect`, or `app info` by default for plain text chat/completion turns.
- Do the minimum discovery needed to construct the next command. Open `core-commands.md`, `messaging-commands.md`, or `management-commands.md` only when the task needs less-common commands, custom inputs, file constraints, workflow commands, workspace commands, or KB commands.
- Prefer `--json` for agent workflows, preserve identifiers returned by prior calls, and avoid restating metadata you do not need for the next step.

## Config Fallback

- Resolution order is: explicit flag, environment variable, config file, built-in default.
- If the task provides `api_key`, `base_url`, or `user`, pass them directly with flags.
- If the task does not provide them, rely on `DIFY_API_KEY`, `DIFY_BASE_URL`, and `DIFY_USER` or the default config file only when they are already expected to exist.
- If required config is still unknown, stop and surface the missing credential or user input instead of guessing.
- Use `app inspect` only when unknown app inputs or file constraints would change the command shape.

## Environment Variables

- `DIFY_API_KEY`
  supplies the API key when `--api-key` is not passed
- `DIFY_BASE_URL`
  supplies the API base URL when `--base-url` is not passed
- `DIFY_USER`
  supplies the default user when `--user` is not passed for commands that accept a user
- Prefer explicit flags when the current task gives you concrete values and use environment variables as shared defaults across multiple CLI calls.
- Do not assume these variables exist unless the task, shell context, or prior command output makes that clear.

## Fast Paths

### One-turn chat

```bash
dify --json chat send --user "<user>" --response-mode blocking --query "<message>"
```

### Multi-turn chat

First turn:

```bash
ROUND_ONE_JSON=$(dify --json chat send --user "<user>" --response-mode blocking --query "<message-1>")
```

Follow-up turn:

```bash
CONVERSATION_ID=$(printf '%s\n' "$ROUND_ONE_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["conversation_id"])')
dify --json chat send --user "<user>" --response-mode blocking --conversation-id "$CONVERSATION_ID" --query "<message-2>"
```

- Treat the snippet above as the reusable pattern for any multi-turn chat task.
- The first successful `chat send` starts the conversation.
- Reuse `conversation_id` directly from the latest completed JSON response for every later turn in the same task.
- Do not fetch conversation history or app metadata unless the task requires it.

## Conversation Continuity Rules

- The first successful `chat send` establishes the conversation for that task.
- Every subsequent turn must reuse the active `conversation_id` from the latest completed response.
- Never send a fresh first-turn message again once a prior first-turn request may have succeeded.
- Preserve returned identifiers from the latest completed response and treat them as the source of truth for the next turn.

## In-Flight Request Discipline

- Allow only one top-level `dify --json chat send` in flight per conversation task at a time.
- If a blocking request is still running, wait for it to finish instead of launching another chat request as a probe, fallback, or diagnosis.
- If the CLI prints built-in retry output, treat it as part of the same in-flight request rather than permission to send another top-level request.
- Do not run side diagnostics that distract from an in-flight chat request unless the task is blocked before any send occurs.

## Failure Handling

- If a request exits cleanly with usable JSON, parse that response and continue from the identifiers it returned.
- If a request exits non-zero before producing usable JSON, retry only that same turn and only after the prior process has fully ended.
- If the outcome of a turn is ambiguous and success cannot be ruled out, stop and surface the ambiguity instead of sending a new message that might fork the conversation.

## Anti-Patterns To Avoid

- Do not issue duplicate chats or restart the conversation just because a blocking call is slow.
- Do not split one conversation task into overlapping sends for the same turn.
- Do not summarize success as a single conversation unless only one conversation-creating send was actually made.

### Upload then send a file

Upload:

```bash
UPLOAD_JSON=$(dify --json files upload --user "<user>" --path "<local-path>")
```

Reuse the upload:

```bash
FILE_ID=$(printf '%s\n' "$UPLOAD_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
dify --json chat send --user "<user>" --response-mode blocking --query "<message>" --file-ref document="$FILE_ID"
```

## File Attachment Mapping

- Valid `transfer_method` values are exactly `local_file` and `remote_url`.
- `--attach [type=]path`
  uploads the local file first, then sends `transfer_method: "local_file"` with `upload_file_id`.
- `--file-ref type=file_id`
  sends `transfer_method: "local_file"` with `upload_file_id: <file_id>`.
- `--remote-file-url type=url`
  sends `transfer_method: "remote_url"` with `url: <url>`.
- Common file `type` values are `document`, `image`, `audio`, and `video`.
- For text files or generic attachments, prefer `document=...` when the type needs to be explicit.

## When To Inspect

Use `dify --json app inspect --user "<user>"` only when at least one of these is true:

- the task requires custom app input fields you do not already know
- the task depends on file-upload limits or accepted file types
- the request payload shape is unclear and would change the command you send

Skip inspection for plain text chat turns with no attachments.

## Open Other Docs Only If Needed

- `core-commands.md`
  Use for config precedence, `--inputs-json`, and global output behavior.
- `messaging-commands.md`
  Use for app/file/completion/chat/workflow commands beyond the fast paths above.
- `management-commands.md`
  Use for workspace and knowledge-base commands.
