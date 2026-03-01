# Employee Interaction Protocol (10-Agent Team)

This protocol makes AI agents operate like employees with clear reporting lines, meetings, and handoffs.

## Meeting cadence
1. **Daily standup (voice transcript required)**
   - PM asks status, blockers, and next action for each role.
2. **Architecture review**
   - TechLead + Networking + DataPersistence + QA align on implementation details.
3. **Design handoff**
   - Product + UX transfer specs to SwiftUI engineer.
4. **Release readiness review**
   - QA + Security + Release manager sign off.

## Interaction rules
- Every update should include:
  - what was done
  - blocker (if any)
  - who is the next owner
- Use `conversation_id` to group turns from a single meeting.
- Add at least one tag (`architecture`, `bug`, `release`, `risk`, etc.).
- If confidence in transcription < 0.9, mark for manual review.

## Handoff template
"I completed <task>. Blocking issue: <issue/none>. Handing off to <agent_id> for <next task>."

## Escalation path
- Feature blocker > 4 hours -> ProgramManagerAgent
- Security/compliance issue -> SecurityComplianceAgent immediately
- Release risk in final 48h -> ReleaseManagerAgent + ProgramManagerAgent
