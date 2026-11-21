---
name: external-learning-landing
description: "Use when the user explicitly asks for external-learning-landing or wants lessons from an external source mapped into an existing local owner surface."
---

# External Learning Landing

Treat the external system as a pattern source, not local authority.

## Workflow

1. Identify how the upstream distributes the relevant component. Compare the local adaptation with that release tag or pinned source revision. For a repository that distributes from its default branch, record the commit. Trace community reports to a merged change, reproduction, or release containing the fix. Distinguish a fix that has landed on the branch from one available to installed users.
2. Extract reusable behavior, data shape, failure handling, evaluation, or workflow patterns without importing foreign branding or runtime assumptions.
3. Classify each candidate as `adopt`, `adapt`, `watch_only`, `reject`, or `no_code_needed`.
4. For `adopt` or `adapt`, map the candidate to one existing local owner surface, intended behavior change, and claim-appropriate acceptance evidence.
5. Prefer current repo/platform/dependency capabilities. Do not create a second source of truth, package manager, runtime, queue, dashboard, or authority plane when a smaller local landing suffices.
6. Implement only when the user authorized implementation; otherwise produce an approval-ready brief.
7. Verify the final local surface and loaded/readback copy when the result is generated, installed, cached, or projected.

## Candidate Record

For each pattern, report:

- external source and inspected version/date;
- classification and reason;
- local owner surface;
- proposed behavior or artifact;
- verification evidence;
- risk, authority boundary, and stop condition.

`no_code_needed` requires fresh local evidence that the current owner already covers the pattern. `watch_only` and `reject` are valid outcomes.

External runtime or authority integration requires both an explicit user request and a supported local integration slot. Domain truth, quality verdicts, release readiness, owner receipts, and runtime authority remain with their existing owners.

For "fully absorb" requests, reuse the active profile's normal completion audit; do not create a second Learning Landing audit or duplicate worktree/subagent policy here.
