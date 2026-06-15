## Project Prompt Architecture Convention

This workspace uses a "centralized contract, distributed references" pattern for prompts:

- `prompts/<name>.md` is the SINGLE SOURCE OF TRUTH — contains the full prompt body (instructions, constraints, output format).
- `.continue/prompts/<name>.prompt.md` — thin reference layer with Continue frontmatter; body is `@prompts/<name>.md`.
- `.claude/commands/<name>.md` — thin reference layer with Claude Code frontmatter; body is `@prompts/<name>.md`.
- `.github/prompts/<name>.prompt.md` — thin reference layer for Copilot; body is `@prompts/<name>.md`.

No reference file should contain substantive prompt content. Each should have only frontmatter + a single `@prompts/<name>.md` reference line.

### When invoked

1. Scan the workspace for all prompt-related files:
   - `prompts/*.md` — check if these are actual contracts (full bodies) or thin references (just frontmatter + `@...`).
   - `.continue/prompts/*.prompt.md` — check body content.
   - `.claude/commands/*.md` — check body content.
   - `.github/prompts/*.prompt.md` — check body content.
   - Any other platform-specific prompt/command files the user mentions.

2. For each file found, classify it:
   - **Contract**: contains substantive prompt instructions/constraints (should live in `prompts/<name>.md`).
   - **Reference**: contains only frontmatter + `@prompts/<name>.md` line (correct pattern).
   - **Duplicate**: contains substantive content that belongs in a contract (needs normalization).

3. For files that are duplicates or misplaced contracts:
   - Extract the substantive prompt body and place it into `prompts/<name>.md` (create if new, merge if existing contract has partial content).
   - Rewrite the original file to be a thin reference: keep platform-specific frontmatter, replace body with `@prompts/<name>.md`.
   - If multiple files under one platform share the same prompt intent, consolidate into a single `prompts/<name>.md` and keep only the necessary platform references.

4. For files already following the pattern (thin references), mark them as conforming — no action needed.

5. Report:
   - Which files were normalized (old → new reference form).
   - Which contracts were created or updated in `prompts/`.
   - Which files already conformed.
   - Any ambiguous cases where you couldn't safely determine if content was a contract or a duplicate — flag these for the user.

<add any extra context here, leave blank to ignore>
