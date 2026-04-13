# CLAUDE.md

## Rules

- Do NOT write, edit, or create any code unless the user explicitly asks you to write code.
- Default to research, analysis, and discussion. Only produce code when directly instructed.

## Conductor Workspace Behavior

- Rename the branch with `git branch -m` at the start of every session before doing anything else.
- Branch names must use the prefix `jonathaneemmett/` and be concise (<30 chars after prefix). Use concrete, specific language — avoid abstract nouns.
- The target base branch for PRs is `main`.
- Only the last message you send is shown to the user by default. Put all essential information in the final response. Earlier messages are collapsed.
- Use the `.context/` directory (gitignored) to share files or notes with other parallel agents in this workspace.
- If a user message seems out of place or intended for a different workspace, ask rather than assuming.
