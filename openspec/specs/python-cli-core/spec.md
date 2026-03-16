# python-cli-core Specification

## Purpose
TBD - created by archiving change add-python-cli. Update Purpose after archive.
## Requirements
### Requirement: CLI entrypoint and installation
The package SHALL expose a `dify` console command that is installable from the Python package and documented for `pipx`, `uv tool`, and editable local installs.

#### Scenario: Console command is available after installation
- **WHEN** a user installs the package through a supported Python installation path
- **THEN** the `dify` command is available on the shell path and launches the CLI help without importing user code

#### Scenario: SDK usage remains unchanged
- **WHEN** existing Python SDK users import `dify_client`
- **THEN** the new CLI packaging does not change or remove the existing Python import surface

### Requirement: Global option and config resolution
The CLI SHALL support global configuration for API key, base URL, timeout, logging, output mode, and default user, with deterministic precedence of command-line flag over environment variable over config-file value over built-in default.

#### Scenario: CLI flag overrides environment
- **WHEN** a user provides `--api-key` and an API key environment variable is also set
- **THEN** the CLI uses the flag value for that invocation

#### Scenario: Missing credentials fail before request dispatch
- **WHEN** a command requires authentication and no API key can be resolved
- **THEN** the CLI exits with a configuration error before constructing a client request

### Requirement: Structured inputs are accepted predictably
The CLI SHALL accept simple structured inputs through repeated `--input key=value` flags and typed or nested inputs through `--inputs-json`, and it MUST treat repeated `--input` values as strings without implicit type conversion.

#### Scenario: Repeated input flags become string fields
- **WHEN** a user runs a command with `--input days=3 --input budget=low`
- **THEN** the request inputs object contains string values `"3"` and `"low"` unless replaced by `--inputs-json`

#### Scenario: JSON inputs override key-value inputs
- **WHEN** a user provides both repeated `--input` flags and `--inputs-json`
- **THEN** the CLI sends the parsed JSON object as the authoritative `inputs` payload

### Requirement: Schema inspection is available for app-aware flows
The CLI SHALL provide an inspection command that retrieves app metadata and application parameters, including `user_input_form` and file upload settings, and emits that information in stable JSON.

#### Scenario: Inspect returns user input schema
- **WHEN** a user runs the app inspection command with `--json`
- **THEN** the output includes the raw or normalized application parameter fields required to discover supported custom inputs

#### Scenario: Schema-aware validation remains optional
- **WHEN** an app does not expose complete metadata or a caller sends raw JSON inputs directly
- **THEN** request commands still run without a mandatory preflight inspection step

### Requirement: Output modes are stable for automation
The CLI SHALL support a JSON output mode for every command, and JSON mode MUST write only machine-readable data to stdout.

#### Scenario: Blocking command returns JSON only
- **WHEN** a user runs a blocking command with `--json`
- **THEN** stdout contains a single valid JSON document and human-oriented summaries are suppressed

#### Scenario: Streaming command returns one event per line
- **WHEN** a user runs a streaming command in JSON mode
- **THEN** stdout emits one JSON object per line in arrival order without non-JSON prefixes or log lines

### Requirement: Error handling and exit codes are explicit
The CLI SHALL distinguish validation/config errors, authentication errors, API response errors, transport failures, and unexpected internal failures through consistent stderr messages and non-zero exit codes.

#### Scenario: Authentication error surfaces cleanly
- **WHEN** the API returns an authentication failure
- **THEN** the CLI exits non-zero, writes the error class and message to stderr, and does not emit partial success output

#### Scenario: Validation error fails locally
- **WHEN** the user provides malformed JSON or an invalid flag combination
- **THEN** the CLI exits before sending a request and reports a validation error on stderr

### Requirement: Canonical command mapping is documented
The CLI SHALL document how public sync SDK methods map to command names, and methods that are duplicate wrappers for the same endpoint SHALL map to a single canonical command.

#### Scenario: Duplicate helper methods do not create duplicate commands
- **WHEN** the SDK exposes both a canonical method and a pagination or response helper for the same endpoint
- **THEN** the CLI spec names one command and documents that it covers the endpoint represented by both methods

#### Scenario: Public sync API families are discoverable
- **WHEN** a user runs root help
- **THEN** the help output lists top-level groups for app, files, completion, chat, workflow, workspace, and kb

