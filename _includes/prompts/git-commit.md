You are in agent mode. Perform the following steps sequentially:

1. Run `git diff --cached` to inspect staged changes. If nothing is staged, run `git status` and inform the user what needs to be staged first.
2. Analyze the staged changes and generate a concise git commit message matching the style below.
3. Execute the commit:
   - Simple changes (subject only): `git commit -m "<subject>"`
   - Complex changes (with body): write the full commit message (subject +
     blank line + body) to a temporary file with real newlines, then run
     `git commit -F <temp_file>` and delete the temp file afterward.
     Use the system temp directory (`/tmp` on Linux/macOS, `%TEMP%` on
     Windows). The temp file must contain the message with actual newline
     characters — not `\n` escape sequences.
4. Show the user the commit message that was used and confirm the commit was successful.

## Commit Message Style

**Subject Line**:
- Format: `type: short description`
- Type: `feat`, `fix`, `refactor`, `chore`, `docs`, `style`, `test`, `ci`, `build`, `perf`
- Imperative mood: "add" NOT "added"
- Lowercase, no trailing period
- One short phrase, be specific but concise

**Body** (only when 3+ distinct changes warrant it):
- Exactly one blank line between subject and body
- Bullet points are TIGHT — no blank lines between bullets
- Use `- ` bullet points ONLY — no prose paragraphs, no section headers
- Each bullet: one short line, lowercase verb start
- 2–6 bullets max, keep it minimal

## Formatting

The body must look like this (note: no blank lines between bullets):

```
subject line

- first bullet
- second bullet
- third bullet
```

## Good Examples (follow these exactly)

```
chore: add AI rules sync mechanism
```

```
feat: integrate Melos and improve workspace tooling
- integrate Melos for package management and automation
- add silent logger and custom test logger initialization
- implement configurable DB paths in DBHelper
```

```
refactor: rewrite sync-rules in Python for cross-platform support
- replace bash script with Python for consistent behavior on
  Windows and Unix-like systems
- add repo-scoped globs to Continue and Cursor frontmatter
```

## Bad Example (DO NOT produce this)

```
chore: migrate build scripts to use Poetry for Python management
Moves Python scripts into scripts/python-scripts/ with a pyproject.toml
so Poetry manages the isolated environment instead of relying on
system-wide Python.
Changes include:
- Add scripts/python-scripts/ directory with pyproject.toml and .gitignore
- Move gen_fastlane_changelog.py...
```
(too verbose, prose paragraphs, "Changes include:" headers, capitalised bullets)

## Rules
- Default to subject-only commits. Add a body only when changes are complex enough.
- Never fabricate details — only describe what's actually in the diff.
- Always execute the commit command. Do not ask for confirmation.

## Command Examples

Simple commit (subject only):
```
git commit -m "chore: add AI rules sync mechanism"
```

Commit with body — write message to a temp file, then use `git commit -F`:
```
cat > /tmp/commit_msg.txt << 'EOF'
feat: integrate Melos and improve workspace tooling

- integrate Melos for package management and automation
- add silent logger and custom test logger initialization
- implement configurable DB paths in DBHelper
EOF
git commit -F /tmp/commit_msg.txt
rm /tmp/commit_msg.txt
```

On Windows (PowerShell), use:
```
$msg = @"
feat: integrate Melos and improve workspace tooling

- integrate Melos for package management and automation
- add silent logger and custom test logger initialization
- implement configurable DB paths in DBHelper
"@
$msg | Out-File -Encoding UTF8 "$env:TEMP\commit_msg.txt"
git commit -F "$env:TEMP\commit_msg.txt"
Remove-Item "$env:TEMP\commit_msg.txt"
```

WRONG — do NOT split bullets across multiple `-m` flags:
```
git commit -m "feat: ..." -m "- first bullet" -m "- second bullet"
```

<add any extra context here, leave blank to ignore>
