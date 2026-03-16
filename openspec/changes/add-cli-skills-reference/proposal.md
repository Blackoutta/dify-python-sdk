## Why

The CLI surface is broad enough that AI agents need a fast, reliable way to discover which commands to use and which flags or configuration details matter before constructing a call. A dedicated skill-oriented reference under `cli-skills/` would reduce command selection errors, shorten prompt context, and make the CLI more usable in agentic workflows.

## What Changes

- Add a `cli-skills/` documentation structure for AI agents that introduces a top-level `skills.md` as the primary index, quick reference, and best-practices guide for CLI usage.
- Define a set of detailed subfiles under `cli-skills/` that break down command groups, supported parameters, required identifiers, configuration expectations, and usage notes at a finer level than the main index.
- Standardize how the top-level index points agents to the right detail files so they can quickly choose commands without loading the full CLI reference every time.
- Document the minimum configuration notes agents should capture, including credential resolution, output mode expectations, and when to prefer structured JSON inputs over scalar flags.

## Capabilities

### New Capabilities
- `cli-skills-reference`: Agent-oriented CLI reference structure, including a main `skills.md` index and detailed command reference files for efficient command discovery and parameter lookup.

### Modified Capabilities

None.

## Impact

- Adds a new documentation and prompt-support surface under `cli-skills/` for AI-agent workflows.
- Requires defining the structure and authoring conventions for `skills.md` and its linked detail files.
- Reuses the existing CLI specifications as source material for command coverage, configuration notes, and grouping decisions.
