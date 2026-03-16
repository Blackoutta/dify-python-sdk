# Core Commands

Use this file for CLI-wide behavior that applies before choosing a business command.

## Scope

- Root options and config precedence
- Output-mode and error-handling expectations
- Structured input rules
- App inspection for schema-aware flows

## Root Options

- `--api-key`: explicit credential for the current invocation
- `--base-url`: override the API base URL
- `--timeout`: request timeout
- `--enable-logging`: enable SDK logging
- `--user`: default user for commands that support it
- `--json`: emit machine-readable output
- `--config`: load a specific config file instead of the default path

## Config Resolution

- Precedence is:
  command-line flag > environment variable > config file > built-in default
- Environment variables:
  `DIFY_API_KEY`, `DIFY_BASE_URL`, `DIFY_USER`
- Default config path:
  `~/.config/dify-client/config.json`
- Built-in base URL default:
  `https://api.dify.ai/v1`

## Input-Shaping Rules

- Use `--input key=value` for simple scalar strings.
- Use repeated `--input` flags to build a flat string-valued object.
- Use `--inputs-json` for typed values, nested objects, arrays, or when exact JSON types matter.
- If both `--input` and `--inputs-json` are supplied, treat `--inputs-json` as the authoritative payload.
- Keep file uploads outside `inputs`; use attachment-oriented flags instead.

## Output Rules

- Prefer `--json` for scripting, tool use, and agent workflows.
- Blocking commands in JSON mode should return one JSON document.
- Streaming commands in JSON mode should return one JSON object per line.
- Human-readable mode may print a concise answer or formatted JSON depending on the command.

## Inspection Workflow

- Use `dify --json app inspect --user <user>` only when the app’s accepted custom fields, file-upload constraints, or payload shape are unknown and that information would change the command you send.
- `app inspect` is useful for app parameters, normalized user-input fields, and file-upload hints, but it is not a default preflight step for plain text chat/completion turns.
- If `DIFY_BASE_URL` or `--base-url` already points at the correct API endpoint, use it directly and avoid inventing extra routing metadata.
- Do not infer hidden app aliases, tenant metadata, or extra identifiers unless the task or returned API data explicitly requires them.
- If metadata is incomplete, you can still call `chat send`, `completion send`, or `workflow run` directly with explicit payloads.

## Error / Exit Guidance

- Validation failures should be treated as local input errors first.
- Authentication failures usually indicate a missing or invalid API key.
- API errors, network errors, and internal errors are surfaced separately; keep stderr available when debugging non-zero exits.

## Command Selection Heuristics

- Need global setup or payload-shaping rules:
  stay in this file
- Need app, file, chat, completion, or workflow commands:
  move to `messaging-commands.md`
- Need workspace or knowledge-base commands:
  move to `management-commands.md`

## Coverage

- OpenSpec capability:
  `python-cli-core`
