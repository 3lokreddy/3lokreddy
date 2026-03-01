# Agentic AI for iOS App Development (Employee-Style)

This repository contains an implementation-ready **Agentic iOS framework** where AI agents work like employees with distinct roles, handoffs, and voice-transcripted collaboration.

## What is included

- `agentic-ios/AGENT_SYSTEM_PROMPT.md`  
  A system prompt for a 10-agent iOS org with architecture and quality enforcement.

- `agentic-ios/agents/employee_org.json`  
  Ten AI employee roles, reporting lines, and handoff relationships.

- `agentic-ios/workflows/ios_app_delivery_workflow.md`  
  End-to-end app delivery flow from intake to post-release.

- `agentic-ios/workflows/employee_interaction_protocol.md`  
  Rules for standups, handoffs, escalation, and voice transcript governance.

- `agentic-ios/transcripts/voice_transcript_schema.md`  
  Transcript schema for voice conversation records.

- `agentic-ios/transcripts/sample_transcripts.json`  
  Sample meeting transcript demonstrating cross-agent communication.

- `agentic-ios/templates/project_blueprint.json` (+ YAML companion)  
  Machine-readable blueprint for project structure and quality gates.

- `agentic-ios/tools/generate_ios_scaffold.py`  
  Scaffold generator for production-style iOS project folders/files.

- `agentic-ios/tools/conversation_lookup.py`  
  Search utility for transcript look-through by speaker, tag, or query.

## Quick start

```bash
python3 agentic-ios/tools/generate_ios_scaffold.py --app-name TaskManager --output ./generated
python3 agentic-ios/tools/conversation_lookup.py --speaker TechLeadAgent
python3 agentic-ios/tools/conversation_lookup.py --tag release
python3 agentic-ios/tools/conversation_lookup.py --query IOS-12
```

## How to run your employee-style agent system

1. Use `agentic-ios/AGENT_SYSTEM_PROMPT.md` as system instructions.
2. Load roles from `agentic-ios/agents/employee_org.json`.
3. Force all progress updates through `employee_interaction_protocol.md`.
4. Persist transcripts with `voice_transcript_schema.md`.
5. Query conversation history with `conversation_lookup.py`.

## Suggested first request

> Build a Task Manager iOS app for iOS 17+ using SwiftUI and MVVM. Run in employee mode with all 10 agents, produce handoff transcripts, and include searchable meeting logs.
