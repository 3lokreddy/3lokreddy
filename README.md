# Agentic AI for iOS App Development

This repository now contains an **implementation-ready Agentic iOS framework** you can use to autonomously build iOS apps with SwiftUI + MVVM.

## What is included

- `agentic-ios/AGENT_SYSTEM_PROMPT.md`  
  A system prompt that enforces architecture, quality gates, lifecycle handling, and delivery output format.

- `agentic-ios/workflows/ios_app_delivery_workflow.md`  
  An end-to-end delivery workflow from intake to post-release.

- `agentic-ios/templates/project_blueprint.json`  
  A machine-readable blueprint for scalable iOS project structure.

- `agentic-ios/tools/generate_ios_scaffold.py`  
  A generator script that creates an iOS folder/file scaffold from the blueprint.

## Quick start

```bash
python3 agentic-ios/tools/generate_ios_scaffold.py --app-name TaskManager --output ./generated
```

This creates:

```text
generated/TaskManager/
  Core/
  Features/
  Shared/
  Models/
  Resources/
  ...starter Swift files
```

## How to use this with an AI agent

1. Use `AGENT_SYSTEM_PROMPT.md` as the system instructions.
2. Feed your app idea and requirements.
3. Ask the agent to execute the workflow in `workflows/ios_app_delivery_workflow.md`.
4. Optionally bootstrap with `generate_ios_scaffold.py`.

## Suggested first request to your agent

> Build a Task Manager iOS app for iOS 17+ using SwiftUI and MVVM. Follow the provided workflow and scaffold. Include loading/empty/error states, local persistence, and unit tests for view models.

---

If you want, I can next extend this with:
- CI/CD (GitHub Actions + fastlane)
- Unit test template generation
- App Store release checklist generator
- Feature module templates (Auth, Dashboard, Settings, Tasks)
