# Dify CLI Fast Path

Use this skill to execute the `dify` CLI with the fewest possible discovery steps.

## Default Behavior

- Assume evaluator environments already provide `DIFY_BASE_URL`, `DIFY_API_KEY`, and `DIFY_USER` unless the task says otherwise.
- In evaluator runs, the app alias is often already encoded in `DIFY_BASE_URL`. Do not try to discover or restate the alias unless the task requires it.
- Prefer one direct CLI attempt over exploratory help calls when the needed flags are already shown below.
- Do not run `dify --help`, `dify <group> --help`, `app inspect`, or `app info` by default for plain text chat/completion turns.
- Do not open `core-commands.md`, `messaging-commands.md`, or `management-commands.md` unless the task needs less-common commands, custom inputs, file constraints, workflow commands, workspace commands, or KB commands.

## Fast Paths

### One-turn chat

```bash
dify --json chat send --user "$DIFY_USER" --response-mode blocking --query "<message>"
```

### Two-turn chatflow

First turn:

```bash
ROUND_ONE_JSON=$(dify --json chat send --user "$DIFY_USER" --response-mode blocking --query "<message-1>")
```

Reuse the returned conversation:

```bash
CONVERSATION_ID=$(printf '%s\n' "$ROUND_ONE_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["conversation_id"])')
dify --json chat send --user "$DIFY_USER" --response-mode blocking --conversation-id "$CONVERSATION_ID" --query "<message-2>"
```

- Reuse `conversation_id` directly from the first JSON response.
- Do not fetch conversation history or app metadata unless the task requires it.

### Upload then send a file

Upload:

```bash
UPLOAD_JSON=$(dify --json files upload --user "$DIFY_USER" --path "<local-path>")
```

Reuse the upload:

```bash
FILE_ID=$(printf '%s\n' "$UPLOAD_JSON" | python -c 'import json,sys; print(json.load(sys.stdin)["id"])')
dify --json chat send --user "$DIFY_USER" --response-mode blocking --query "<message>" --file-ref document="$FILE_ID"
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

Use `dify --json app inspect --user "$DIFY_USER"` only when at least one of these is true:

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
