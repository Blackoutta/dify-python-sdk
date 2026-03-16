## Context

The repository already defines the CLI command surface in OpenSpec, but those specs are optimized for feature coverage and implementation planning rather than low-latency agent consumption. AI agents working through terminal workflows need a compact entrypoint that helps them choose the right command group, understand required identifiers and flags, and know when to inspect metadata or send structured JSON.

The new `cli-skills/` folder is intended to bridge that gap without duplicating the entire CLI documentation set in a single file. The design needs to keep the top-level guide concise while preserving enough detail in linked files for accurate command construction.

## Goals / Non-Goals

**Goals:**
- Provide a top-level `cli-skills/skills.md` file that serves as the primary entrypoint for AI agents.
- Define a predictable file organization for detailed command reference files under `cli-skills/`.
- Ensure the skill docs capture command-selection guidance, key parameters, and CLI configuration notes that affect correctness.
- Keep the new skill content aligned with the existing CLI specifications so it can evolve with the CLI contract.

**Non-Goals:**
- Redefine the CLI runtime behavior, command names, or flag semantics.
- Replace README-level user documentation or full CLI help output.
- Introduce generated docs tooling in this change.

## Decisions

Create a two-level documentation structure under `cli-skills/`.
Rationale: A single file would become too large for efficient prompt context, while deeply nested docs would make discovery harder. A concise `skills.md` index plus focused subfiles balances quick scanning with detailed lookup.

Organize detailed files by CLI capability or command family rather than one file per command.
Rationale: The existing CLI specs are grouped into core, messaging, and management capabilities. Mirroring those groupings keeps the skill docs easy to maintain and lets agents load only the family they need.
Alternative considered: one file per command. Rejected because it would create too many small files and increase navigation overhead for closely related commands.

Treat `skills.md` as both a routing layer and a best-practices guide.
Rationale: Agents need more than links; they also need short heuristics for choosing JSON output, handling credentials, using `--inputs-json`, and inspecting app metadata before issuing requests.

Derive subfile content from the authoritative CLI specs instead of inventing separate command contracts.
Rationale: This minimizes drift and keeps the skill layer aligned with the existing OpenSpec requirements. The skill docs can summarize and reorganize the information, but they should not introduce behavior that contradicts the CLI specs.

## Risks / Trade-offs

[Documentation drift between specs and skill docs] -> Mitigation: explicitly map each detail file to the relevant CLI capability specs and include maintenance tasks for cross-checking command coverage.

[Top-level guide becomes too verbose for agents] -> Mitigation: keep `skills.md` focused on quick reference, routing, and best practices, with command-by-command detail pushed into subfiles.

[Incomplete parameter guidance causes incorrect command construction] -> Mitigation: require each detail file to call out required identifiers, structured input expectations, and notable response/config behaviors for the commands it covers.

## Migration Plan

Create the `cli-skills/` structure, author `skills.md`, add the detailed command family files, and validate the content against the active CLI specs before implementation is considered complete. No runtime migration or rollback steps are required because this change adds documentation only.

## Open Questions

Should the detail files mirror the exact names of the CLI capability specs (`core`, `messaging`, `management`) or use more agent-oriented names that are easier to scan at a glance?
