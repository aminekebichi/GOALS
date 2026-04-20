---
name: create-pr
version: 1
description: Creates a PR with C.L.E.A.R. framework review template and AI disclosure metadata
---

# /create-pr

Creates a well-structured pull request using the C.L.E.A.R. framework with AI disclosure.

## Usage

```
/create-pr [branch] [base-branch]
```

If no arguments provided, uses current branch → main.

## Steps

1. Run `git diff [base]..[branch] --stat` to summarize what changed
2. Run `git log [base]..[branch] --oneline` to list commits
3. Draft PR title (≤70 chars, imperative mood)
4. Draft PR body using the C.L.E.A.R. template below
5. Run `gh pr create --title "..." --body "..."` to open the PR

## C.L.E.A.R. PR Template

```markdown
## Context
<!-- Why is this change needed? What problem does it solve? -->

## Logic
<!-- How was it implemented? Key decisions made. -->

## Evidence
<!-- Tests passing, screenshots, or benchmark results -->
- [ ] Unit tests pass (`npm run test:run`)
- [ ] Type check passes (`npx tsc --noEmit`)
- [ ] Lint passes (`npm run lint`)

## Alternatives
<!-- What other approaches were considered and why this one was chosen -->

## Review
<!-- Specific asks for reviewers — what to focus on, what to ignore -->

---
🤖 **AI Disclosure**: ~75% AI-generated | Human review: Applied | Tool: Claude Code (claude-sonnet-4-6)
```

## Notes

- Always link the related GitHub Issue with `Closes #N`
- Assign at least one reviewer
- Label with `feat`, `fix`, `chore`, or `docs` as appropriate
