# iOS Delivery Workflow (Agent-Operated)

## 0) Intake
- Capture app idea in one sentence.
- Define user personas and top 3 jobs-to-be-done.
- Confirm target iOS version and monetization model.

## 1) Product Scope
- Draft MVP feature list (must-have vs later).
- Define non-functional constraints:
  - Offline behavior
  - Security/privacy requirements
  - Performance targets

## 2) Architecture Setup
- Initialize SwiftUI app.
- Create folder baseline:
  - `Core/`
  - `Features/`
  - `Shared/`
  - `Models/`
  - `Resources/`
- Add environment config and log abstraction.

## 3) Feature Implementation Loop
For each feature:
1. Define user story + acceptance criteria.
2. Create domain models and service protocols.
3. Build ViewModel + state machine.
4. Build SwiftUI View.
5. Add loading/empty/error UI states.
6. Add tests (unit first, UI if needed).
7. Validate against acceptance criteria.

## 4) Quality Gates
- No networking in views.
- No hard-coded secrets.
- Lifecycle handlers for background/restore.
- Error mapping from transport -> domain -> UI.
- Basic observability (logs + metrics hooks).

## 5) Release Prep
- Simulator and device QA pass.
- Version bump + release notes.
- App Store metadata bundle:
  - Description
  - Screenshots
  - Privacy policy
  - What's New notes

## 6) Post-Release
- Monitor crash reports and analytics.
- Rank issues by severity/impact.
- Roll out patch releases with changelog discipline.
