---
name: engez-pipeline
description: Full feature pipeline orchestrator for ENGEZ. Run after /speckit-specify to continue the development loop — clarify, plan, tasks, analyze — then hand off to GLM for implementation, then review with TDD + design hardening. Use when user says "run pipeline", "continue pipeline", "engez pipeline", or after completing speckit-specify.
---

# ENGEZ Feature Pipeline

Orchestrates the full feature development loop from the ENGEZ Skills Guide.
Call this **after** `/speckit-specify` has produced `spec.md`.

GLM handles implementation. Claude handles spec workflow, testing, and design quality.

## Pre-Flight Checks

Before running any step, perform these checks silently:

1. **Locate the active feature spec directory**: Find the most recently modified `spec.md` under `specs/`. The parent directory is the active feature dir. Store it as `$FEATURE_DIR`.
2. **Verify `spec.md` exists** in `$FEATURE_DIR`. If not, stop and tell the user: "No spec.md found. Run `/speckit-specify <feature>` first."
3. **Detect current branch**: Run `git branch --show-current` — confirm it matches a feature branch pattern (e.g., `NNN-feature-name`). Warn if on `master`.

## Pipeline Steps

Execute each step in order. For each step, check the skip condition first. If the condition is met, print `[SKIP] <step> — <reason>` and move to the next step. If the condition is NOT met, execute the step.

**Between each step, ask the user**: "Step N complete. Continue to next step? (y/skip/stop)"
- `y` or Enter → proceed
- `skip` → skip the next step
- `stop` → halt pipeline, print summary of what was completed

---

### Step 0: Design Foundation (ONE-TIME)

**Skip condition**: Both `PRODUCT.md` AND `DESIGN.md` exist in the project root.

**If not skipped**:
- Tell the user: "Design foundation files (PRODUCT.md + DESIGN.md) don't exist yet. These are created once per project and all design commands read them."
- Ask: "Run `/impeccable teach` now to set up design foundations? (y/n)"
- If yes: Execute `/impeccable teach` (interactive interview)
- If no: Print "[DEFERRED] You can run `/impeccable teach` later. Design quality steps (harden/polish) will still work but without project-specific design context."

---

### Step 1: Clarify the Spec

**Skip condition**: `$FEATURE_DIR/spec.md` contains a section heading matching any of:
- `## Clarifications`
- `## Open Questions (Resolved)`
- `## Clarification`
- `<!-- clarified -->`

**If not skipped**:
- Execute `/speckit-clarify`
- This asks 5 targeted questions to sharpen underspecified areas in the spec.

---

### Step 2: Generate Plan

**Skip condition**: `$FEATURE_DIR/plan.md` exists AND has more than 10 lines of content.

**If not skipped**:
- Execute `/speckit-plan`
- This produces `plan.md` with architecture, schemas, API contracts, and component design.

---

### Step 3: Generate Tasks

**Skip condition**: `$FEATURE_DIR/tasks.md` exists AND has more than 10 lines of content.

**If not skipped**:
- Execute `/speckit-tasks`
- This produces `tasks.md` with dependency-ordered implementation tasks.

---

### Step 4: Analyze Consistency

**Skip condition**: Never skipped. Always runs.

- Execute `/speckit-analyze`
- This is a **read-only** cross-artifact consistency check across spec.md, plan.md, and tasks.md.
- Report any inconsistencies found.

---

### GATE: Handoff to GLM

After Step 4, print the following handoff summary:

```
====================================
  PIPELINE PAUSED — GLM HANDOFF
====================================

Spec-Kit artifacts are ready:
  - spec.md  ✓ (clarified)
  - plan.md  ✓ (architecture)
  - tasks.md ✓ (ordered tasks)
  - analyze  ✓ (consistency checked)

Next: Implement using GLM.
  Location: $FEATURE_DIR/tasks.md

After GLM completes implementation, call:
  /engez-pipeline review

This will run:
  → /tdd             (test GLM's code)
  → /impeccable harden (RTL, i18n, edge cases)
  → /impeccable polish  (final quality pass)
====================================
```

**Stop here.** Do not continue to review steps unless the user explicitly says `/engez-pipeline review` or "continue pipeline" or "run review" or "review the code".

---

### Step 5: TDD Review (post-GLM)

**Skip condition**: Never skipped.

- Execute `/tdd`
- Focus on testing the code that GLM wrote for this feature.
- Target: public API behavior, critical paths, edge cases.
- Report any bugs or failures found. Format each issue as:
  ```
  BUG: <file>:<line> — <description>
  FIX: <what needs to change>
  ```

---

### Step 6: Harden

**Skip condition**: Never skipped.

- Execute `/impeccable harden`
- Focus areas for ENGEZ:
  - **RTL layout**: CSS logical properties, bidirectional text
  - **i18n**: Arabic/English string overflow, date/number formatting
  - **Offline**: Edge cases when network drops mid-operation
  - **Extreme inputs**: Long Arabic text, emoji in expense names, special characters
  - **Error states**: Empty states, loading states, network error states

---

### Step 7: Polish

**Skip condition**: Never skipped.

- Execute `/impeccable polish`
- Final quality pass: spacing, alignment, consistency, typography, dark mode.

---

## Pipeline Summary

After the final step (or when stopped), print a summary:

```
ENGEZ PIPELINE — COMPLETE
========================
Feature: <feature name from spec.md title>
Directory: $FEATURE_DIR

Steps completed:
  [✓] Design Foundation
  [✓] Clarify
  [✓] Plan
  [✓] Tasks
  [✓] Analyze
  [—] Implement (GLM)
  [✓] TDD Review
  [✓] Harden
  [✓] Polish

Issues found: <count from TDD + harden>
========================
```

## Arguments

If called with `$ARGUMENTS`:
- `review` or `post-glm` → Skip to Step 5 (TDD Review), assuming spec steps are done
- `plan-only` → Run Steps 0-4 only, then stop at GLM handoff
- No argument → Run from Step 0, stopping at GLM handoff
