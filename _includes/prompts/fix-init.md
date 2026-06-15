## Project AI Agent Initialization Convention

This workspace initializes AI agent integration paths uniformly:

1. **Claude Code** — `CLAUDE.md` + `.claude/commands/` slash commands
2. **GitHub Copilot** — `.github/copilot-instructions.md`
3. **Continue IDE** — `.continue/config.yaml` + `.continue/prompts/` + `.continue/rules/CONTINUE.md`

All paths avoid duplicating rules. They uniformly point to `AGENTS.md`
as the single source of truth, achieving a "define once, apply
everywhere" structure.

### When invoked

1. Check whether `AGENTS.md` exists at the repo root.
   - If it exists, read it to capture the current authoritative rules.
   - If it does NOT exist, scan for AI agent initialization/rule files
     with substantive content (e.g. `CLAUDE.md`,
     `.github/copilot-instructions.md`,
     `.github/instructions/*.instructions.md`, `.continue/rules/*.md`,
     `GEMINI.md`, `.cursor/rules/*`, etc.) and consolidate their content
     into a new `AGENTS.md` at the repo root — merge overlapping
     sections, dedupe, and organize by topic. This becomes the
     authoritative source that step 4 points everything else back to.
2. Scan the workspace for AI agent initialization files belonging to
   any plugin/tool (Claude Code, Copilot, Continue, Cursor, Gemini, etc.),
   including ones not listed above.
3. For each file found, check whether it follows the convention — i.e.
   it references `AGENTS.md` (or its content) rather than duplicating
   rule text inline.
4. For any file that does NOT follow this pattern, rewrite it to point to
   `AGENTS.md` instead, removing the duplicated content while preserving
   any platform-specific frontmatter or registration needed for that tool.
   - **Continue**: if multiple files exist under `.continue/rules/`,
     consolidate them into a single `.continue/rules/CONTINUE.md` that
     references `AGENTS.md`, removing the now-redundant files.
5. Report which files were fixed, which already conformed, which were
   merged into a newly created `AGENTS.md`, and any cases where you
   couldn't safely consolidate (e.g. conflicting or contradictory rules
   across files) — flag these for the user rather than guessing.

<add any extra context here, leave blank to ignore>
