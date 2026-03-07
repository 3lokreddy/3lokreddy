# CLAUDE.md

## Repository Overview

This is a **GitHub profile repository** (`3lokreddy/3lokreddy`). GitHub treats this as a special repository: the `README.md` file in the root is automatically displayed on the user's public GitHub profile page at `github.com/3lokreddy`.

There is no application source code, build system, or test suite — the sole artifact is the profile README.

## Repository Structure

```
3lokreddy/
└── README.md   # GitHub profile bio (rendered on github.com/3lokreddy)
```

## Key Conventions

### README.md
- Written in **GitHub Flavored Markdown (GFM)**.
- Content is displayed publicly on the GitHub profile — keep it professional and accurate.
- The HTML comment block at the bottom (`<!-- ... -->`) is the default GitHub placeholder; it is hidden from rendered output and can be left or removed.
- Emoji shortcodes (`:wave:`) and Unicode emoji are both supported by GitHub's renderer.

### Branching
- Default branch: `main` (remote) / `master` (local default).
- Feature branches follow the pattern: `claude/<description>-<id>` (e.g., `claude/add-claude-documentation-Y5wYq`).

### Commits
- Commit messages should be short and descriptive (e.g., `"Update README with new skills"`).
- There is no linting, formatting, or CI pipeline to satisfy before committing.

## Development Workflow

Since this repo contains only a Markdown file:

1. **Edit** `README.md` directly.
2. **Preview** changes locally with any Markdown renderer (e.g., VS Code preview, `grip`, or GitHub's web editor preview).
3. **Commit and push** to `main`/`master` — changes go live on the profile immediately after push.

```bash
git add README.md
git commit -m "Update profile README"
git push origin main
```

## What AI Assistants Should Know

- Do **not** add source code, package managers, or build tooling unless the user explicitly asks to turn this into a project repository.
- Changes to `README.md` are immediately public; avoid adding sensitive information (tokens, emails, etc.).
- No tests, linters, or CI checks exist — there is nothing to run before committing.
- If the user asks to add a new project, the correct action is to create a **new repository** rather than adding source code here.
