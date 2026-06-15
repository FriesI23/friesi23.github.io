# Create Rule

You are maintaining a multi-agent rules architecture with this structure:

- `rules/<name>.md` is the SINGLE SOURCE OF TRUTH for a rule's
  content — the actual conventions, architecture notes, or
  documentation guidance.
- `.continue/rules/<name>.md` and
  `.github/instructions/<name>.instructions.md` are thin reference
  layers for Continue and Copilot. Each contains only the
  platform-specific frontmatter (Continue: `name`, `description`,
  `globs`, `alwaysApply`; Copilot: `applyTo` glob) plus a single
  `@rules/<name>.md` reference that pulls in the rule body. Both
  platforms support multi-file/glob scoping natively, so prefer one
  rule file with the right `globs`/`applyTo` over splitting by
  directory. Never duplicate rule content into these files.
- For Claude Code, scope is expressed via placement rather than globs:
  add an `@rules/<name>.md` import line to the `CLAUDE.md` that covers
  the relevant directory — root `CLAUDE.md` for workspace-wide rules,
  or a nested `<dir>/CLAUDE.md` for rules scoped to that subtree.
  Create the nested `CLAUDE.md` if it doesn't exist yet.

## When invoked

1. Detect repo scope: classify each repo root in the workspace as
   `code`, `docs`, or `mixed`, and identify which platforms
   (`.continue/`, `.github/`, `CLAUDE.md`) are already in use.
2. Read existing `rules/*.md` and platform reference files first.
   Update or extend an existing rule instead of duplicating intent.
   Use lexicographic ordering (`01-...`, `02-...`) for new rule files.
3. Based on the user's description below, write/update
   `rules/<name>.md` with concrete, project-specific guidance — no
   generic best-practice filler. Keep it scannable: short sections and
   bullets. State explicitly where things live, how they're named, and
   what to consult before editing. If a convention can't be verified,
   omit it rather than fabricating it.
4. For each platform actually in use, write/update the matching
   reference file (or `CLAUDE.md` import) with the `globs`/`applyTo`
   scope that fits the rule. Use `alwaysApply: true` (Continue) only
   for rules that must always load.

## Output

Output each created/updated file as a separate fenced block headed by
its path, e.g.:

```rules/<name>.md
<rule content>
```

```.continue/rules/<name>.md
---
name: <name>
description: <description>
globs: <glob or omit>
---
@rules/<name>.md
```

```.github/instructions/<name>.instructions.md
---
applyTo: <glob>
---
@rules/<name>.md
```

End with a short note listing which repos were classified as code,
docs, or mixed; which files were created or updated; and any missing
evidence or follow-up verification needed.

Derive `<short-kebab-case-name>` from the description for `<name>`.

User's description: <fill in your rule description here>
