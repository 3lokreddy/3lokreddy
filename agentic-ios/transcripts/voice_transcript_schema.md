# Voice Transcript + Conversation Lookup Schema

Use this schema so agents communicate like employees in standups, handoffs, and review calls.

## Transcript record format (JSON)
```json
{
  "conversation_id": "conv-2026-03-01-001",
  "meeting_type": "daily-standup",
  "timestamp_utc": "2026-03-01T09:00:00Z",
  "speaker_agent_id": "ProgramManagerAgent",
  "speaker_role": "Program Manager",
  "audio_meta": {
    "channel": "voice",
    "duration_seconds": 23,
    "confidence": 0.97
  },
  "text": "Today we close milestone M2. Tech Lead will approve architecture by noon.",
  "tags": ["milestone", "handoff", "M2"],
  "linked_items": ["ticket:IOS-42", "doc:architecture-v2"]
}
```

## Required fields
- `conversation_id`: groups all turns in a meeting.
- `speaker_agent_id`: must match one of the 10 employee agent IDs.
- `text`: final transcript text after speech-to-text.
- `tags`: searchable labels (`bug`, `release`, `architecture`, etc.).

## Conversation lookup patterns
- By speaker: "show all TechLeadAgent updates"
- By tag: "find all transcript lines tagged release"
- By ticket/doc: "what was said about IOS-42"
- By timeframe: "all blockers discussed today"

## Governance
- Keep sensitive user data redacted in transcripts.
- Include confidence score for voice-text auditing.
- Store raw audio separately from transcript index.
