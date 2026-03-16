## ADDED Requirements

### Requirement: Main skill index provides fast command discovery
The repository SHALL provide a `cli-skills/skills.md` file that serves as the primary entrypoint for AI agents and summarizes how to choose the correct CLI command reference before loading detailed documentation.

#### Scenario: Agent starts from the main skill index
- **WHEN** an AI agent opens `cli-skills/skills.md`
- **THEN** the file presents a quick reference for the available CLI command families and directs the agent to the relevant detailed file for deeper parameter guidance

### Requirement: Main skill index captures CLI best practices and configuration notes
The `cli-skills/skills.md` file SHALL document the key CLI usage conventions that agents need to avoid incorrect command execution, including credential/config resolution, output mode guidance, and when to prefer structured JSON inputs or metadata inspection.

#### Scenario: Agent needs to plan a command invocation
- **WHEN** an AI agent consults `cli-skills/skills.md` before constructing a CLI command
- **THEN** the file highlights the configuration and request-shaping notes the agent must account for before selecting flags and payload formats

### Requirement: Detailed command files provide parameter-level guidance
The repository SHALL provide detailed files under `cli-skills/` that group related CLI commands and describe the purpose, notable parameters, required identifiers, and usage notes for the commands in that group.

#### Scenario: Agent needs details for a specific command family
- **WHEN** an AI agent follows a link from `cli-skills/skills.md` to a command-family detail file
- **THEN** the detail file lists the commands in scope and explains the parameters or payload expectations needed to construct a valid invocation

### Requirement: Skill docs stay aligned with CLI capabilities
The `cli-skills/` documentation structure SHALL map its top-level routing and detailed files to the existing CLI capability boundaries so that command coverage and maintenance can be traced back to the authoritative CLI specs.

#### Scenario: Maintainer checks command coverage
- **WHEN** a maintainer reviews the `cli-skills/` content against the CLI specification set
- **THEN** the file structure and command-group coverage make it possible to confirm which CLI capability each skill document represents
