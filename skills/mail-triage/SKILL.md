---
name: mail-triage
description: Use when triaging today's new emails through Apple Mail, filtering review invitations, or explaining manuscript status updates and thread context; route full-inbox, multi-day, synced, or auditable work to codex-mail-workbench.
---

# Mail Triage

## Overview

This skill is the lightweight Apple Mail path for deciding which new emails are
worth attention. It is optimized for same-day screening, academic inboxes,
review invitations, manuscript status updates, and ongoing conversations. It is
a companion to `codex-mail-workbench`, not a replacement for it.

## Route Selection

Choose exactly one mailbox-fact route before inspecting messages.

Use this skill with `apple-mail` when the request is primarily:

- a quick screen of today's new mail;
- explicitly about Apple Mail or Mail.app;
- dependent on UI-local mailbox, read/unread, or message state;
- a narrow thread or status lookup that does not require a fresh IMAP sync.

Use `codex-mail-workbench` instead when the request requires:

- the complete current inbox, multiple dates, or every configured account;
- explicit IMAP sync freshness or broad historical search;
- bulk classification, cleanup, or an auditable batch operation;
- stable manuscript first-author routing across recipient headers and history.

Honor a route the user names explicitly. Do not scan the same request through
both routes. If the Apple Mail screen reveals that the workbench is required,
state the handoff and restart fact gathering there instead of combining results.

## Shared Private Policy

Before making personal triage or routing judgments, read the OPL Relay private
workspace entry point when it exists:

1. Use `$OPL_RELAY_WORKSPACE/AGENTS.md` when `OPL_RELAY_WORKSPACE` is set.
2. Otherwise use `~/.opl-relay/workspaces/default/AGENTS.md` when present.
3. Follow the required read order from that entry point.

The overlay supplies policy and personal context only. While this route is
active, mailbox facts still come exclusively from Apple Mail; do not run
`codex-mail` merely to apply the shared policy. If the overlay is unavailable,
continue with this skill's built-in rules and
[`references/journal-evaluation.md`](references/journal-evaluation.md), and state
that private policy coverage was unavailable.

Keep route identifiers isolated:

- Apple Mail uses the exact `id`, `account`, and `mailboxPath` tuple.
- Mail Bench uses `storage_ref`.
- Never translate, substitute, or combine these handles. Execute a follow-up
  operation only through the route that produced its handle.

## Workflow

1. Select the Apple Mail route and load `apple-mail` first.
2. Read the shared private policy entry point when available.
3. Start with lightweight metadata, not full bodies:

```bash
python3 ~/.codex/skills/apple-mail/scripts/apple_apps.py mail triage-meta --limit 8 --include-read --on-date "YYYY-MM-DD"
```

4. Keep messages required by the shared private policy. Without that overlay,
   keep at least:

- review invitations
- manuscript status updates
- manuscript conversations or follow-up threads
- editorial responsibilities
- direct academic, business, collaborator, or institutional requests

5. For each kept email, use the exact `id`, `account`, and `mailboxPath` to read the body:

```bash
python3 ~/.codex/skills/apple-mail/scripts/apple_apps.py mail read --id <id> --account "<account>" --mailbox-path "<mailbox>"
```

6. If the current email does not explain enough context, use thread-aware search with the best available clue. The clue can be a manuscript id, title fragment, sender, order number, project name, meeting code, or any other structured identifier.

```bash
python3 ~/.codex/skills/apple-mail/scripts/apple_apps.py mail search --account "<account>" --query "<manuscript id or title fragment>" --limit 10 --include-read
```

7. Read 1-2 related emails from the returned thread context only if the current email still lacks enough detail.
8. If a decision requires complete-inbox coverage, fresh IMAP state, stable batch
   handles, or recipient evidence Apple Mail cannot expose, hand off to
   `codex-mail-workbench` and restart that part of the inspection there.

## Review Invitations

- Extract the journal name from the subject, sender, and body.
- Use model knowledge first. If the journal is clearly reputable and well known, keep it.
- If the journal quality is uncertain, use a dedicated search or retrieval tool
  to inspect official journal or publisher pages; follow the active browser
  routing policy only when page interaction is needed.
- If the journal is still unfamiliar, weak, spammy, or hard to verify, treat it as not worth attention and ignore it.

Read [`references/journal-evaluation.md`](references/journal-evaluation.md) when
judging invitation quality if the shared private overlay does not provide a
more specific rule.

## Status Updates And Conversations

These emails must not be summarized as title-only notifications. Explain:

- which manuscript this is about
- what exactly changed
- whether review is complete, proof is ready, revision is reactivated, or someone is waiting for your response
- what this means in the current thread context
- whether you likely need to act

If the user may not remember the thread context, reconstruct it from the current email and the related thread results.

## Output Format

Use concise Chinese output and the shared private report contract when it was
loaded. For each email worth attention, include:

- email type
- manuscript or journal name
- what happened
- why it matters
- whether action is needed

For low-value review invitations, one short dismissal line is enough.

## Notes

- Prefer `triage-meta` over `recent` for daily screening because it is lighter and faster.
- Treat `search` as the main tool for context recovery after a candidate email is identified.
- Do not browse unless the journal quality is uncertain or the user explicitly wants verification.
- For web checks, prefer official sources through the active research route.
- Reading shared policy never grants permission to send, delete, archive, move,
  or mark mail.
- Do not claim IMAP freshness, complete-inbox coverage, or a `storage_ref` from
  the Apple Mail route.
