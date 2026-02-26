# CLAUDE.md

This file provides guidance for Claude and other AI assistants working in this repository.

## Overview

This is a GitHub profile README repository. The repository name matches the GitHub
username (`3lokreddy/3lokreddy`), which causes GitHub to automatically display the
contents of `README.md` on the public profile page at https://github.com/3lokreddy.

The sole purpose of this repository is to maintain that profile README. It contains
no application code, no dependencies, and no build system.

## Repository Structure

```
.
├── README.md    # GitHub profile README, displayed at https://github.com/3lokreddy
└── CLAUDE.md    # This file - guidance for AI assistants
```

## Git Workflow

### Branches

- `master` — the primary branch; changes here drive what appears on the live profile
- Feature or documentation changes should be made on a descriptive branch and
  merged to `master` via pull request
- The remote exposes both `origin/main` and `origin/master`; target `master` when pushing

### Commit Messages

Use short, descriptive imperative-mood messages:

    Update README to add current projects section
    Fix typo in bio line

Avoid vague messages like "update" or "changes". Since this repo has a single file
and single purpose, the commit message should convey intent without reading the diff.

### Pull Requests

Changes to `README.md` should go through a pull request to `master` rather than
being committed directly. This gives an opportunity to preview changes before they
appear on the public profile.

## Working with README.md

`README.md` is rendered as the GitHub profile page. When making changes:

- GitHub renders the file as Markdown. Standard GitHub Flavored Markdown (GFM)
  is supported, including emoji shortcodes (e.g., `:wave:`), task lists, and
  relative image links.
- Changes are visible publicly as soon as they are merged to `master`. There is
  no staging environment.
- Keep the tone personal and first-person. This is a human profile page, not
  technical documentation.
- Do not add large blocks of auto-generated or templated content without the
  owner's explicit review. The profile represents a real person.

## AI Assistant Guidelines

### What this repository is for

This repository exists to maintain a personal GitHub profile. Do not treat it as a
general-purpose project to add structure to. Resist the urge to scaffold directories,
add configuration files, or introduce tooling unless the owner explicitly asks for it.

### Making changes

- Prefer minimal, targeted edits over rewrites.
- When asked to improve the README, preserve the owner's voice and intent.
  Suggest improvements rather than replacing content wholesale.
- Do not infer unstated goals. If the owner wants to add a project showcase,
  a skills section, or badges, they will describe what they want.

### What to avoid

- Do not create placeholder files, empty directories, or stub configurations.
- Do not add `.gitignore`, `package.json`, `LICENSE`, or other boilerplate
  unless explicitly requested. These files would clutter a repository that is
  intentionally documentation-only.
- Do not fabricate project history or capabilities in the README.

## Future Development

If this repository expands to include code (e.g., scripts, tools, or projects
hosted alongside the profile), this section should be updated to document:

- The language and runtime in use
- How to build and test the code
- Any added conventions or linting rules

Until then, none of those sections apply and should not be added preemptively.
