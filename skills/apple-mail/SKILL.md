---
name: apple-mail
description: Use only for Apple Mail or Mail.app tasks on macOS, including listing accounts and mailboxes, inspecting or searching messages, and reading, marking, archiving, moving, or deleting mail. Do not use for other Apple native apps, webmail, IMAP-only work, or generic macOS automation.
---

# Apple Mail

## Overview

This skill is the macOS Mail.app entry point. It implements `mail.*` automation
with JSON output designed for agent workflows.

For local synced mail archives, full-text FTS5 search, or auditable draft/send
workflows, prefer `opl-relay` (or `himalaya` for direct IMAP access) as the
canonical owner. When `opl-relay` is installed, `scripts/apple_apps.py`
delegates supported read-only Mail.app operations (`accounts`, `mailboxes`,
`recent`, `read`) to `opl-relay` automatically and falls back to the minimal
Mail.app JXA script for local-only operations (`triage-meta`, `mark`, `move`,
`archive`, `delete`) or when `opl-relay` is unavailable.

## When to Use

- User asks to manage Apple Mail on this Mac
- User wants to inspect inboxes, triage messages, archive clutter, or move mail between folders
- User specifically wants local Mail.app behavior, not Gmail web UI or IMAP libraries

Do not use this skill for webmail sites opened in a browser.

## Command Surface

The helper lives next to this skill at `scripts/apple_apps.py`.
Optional `--backend {auto,mail-app,opl-relay,himalaya}` selects delegation vs
direct Mail.app fallback (default: `auto`).

Read-only commands:

```bash
python3 scripts/apple_apps.py mail accounts
python3 scripts/apple_apps.py mail mailboxes --account "iCloud"
python3 scripts/apple_apps.py mail recent --account "SYSU" --limit 1 --include-read
python3 scripts/apple_apps.py mail triage-meta --account "SYSU" --mailbox-path "INBOX" --limit 5 --include-read --on-date "2026-03-18"
python3 scripts/apple_apps.py mail search --account "SYSU" --query "invoice" --limit 20
python3 scripts/apple_apps.py mail search --account "SYSU" --query "Beta view" --limit 10 --include-read --include-body
python3 scripts/apple_apps.py --backend opl-relay mail search --account "SYSU" --query "invoice" --limit 20
python3 scripts/apple_apps.py mail read --id 141819 --account "SYSU" --mailbox-path "INBOX"
```

Mutation commands (Mail.app JXA fallback only):

```bash
python3 scripts/apple_apps.py mail mark --id 141819 --account "SYSU" --mailbox-path "INBOX" --read true
python3 scripts/apple_apps.py mail move --id 141819 --account "SYSU" --mailbox-path "INBOX" --to-mailbox "Archive"
python3 scripts/apple_apps.py mail archive --id 141819 --account "SYSU" --mailbox-path "INBOX"
python3 scripts/apple_apps.py mail delete --id 141819 --account "SYSU" --mailbox-path "INBOX"
```

## Workflow

1. For daily inbox triage, start with `triage-meta`.
2. For point lookups and thread recovery, use `search` (or `--backend opl-relay` for full local FTS5 search).
3. For one-message inspection, use `recent`.
4. Capture the returned `id`, `account`, and `mailboxPath`.
5. Pass those exact values into `read`, `mark`, `move`, `archive`, or `delete`.
6. For creating, reviewing, or sending drafts, hand off to `opl-relay draft`.

## Current Limits

- Header unfolding, RFC 2047 decoding, and date/Received parsing use Python's standard library `email.parser.HeaderParser` and `email.utils.parsedate_to_datetime`.
- `triage-meta` reads lightweight metadata from headers without loading message bodies.
- `search` prefers lightweight thread-aware matching when `--include-body` is not set; `--include-body` performs two-stage recall and batched body reads. For full-mailbox indexed search, pass `--backend opl-relay`.
- `read`, `mark`, `move`, `archive`, and `delete` are verified for top-level mailbox paths such as `INBOX` and `Archive`.
- After `move` or `archive`, Mail may assign a new internal numeric `id`; refresh it with another `recent` or `read` before the next mutation.

## Safety Rules

- Default to read-only exploration first.
- Before destructive actions (`move`, `archive`, `delete`), identify the exact target messages from `recent` or `search`.
- Prefer `mailboxPath` over `mailbox` when a folder name could be ambiguous.
