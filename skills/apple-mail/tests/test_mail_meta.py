from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "apple_apps.py"
SPEC = importlib.util.spec_from_file_location("apple_apps", SCRIPT_PATH)
assert SPEC and SPEC.loader
apple_apps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(apple_apps)


def test_extract_header_metadata_prefers_explicit_date_header() -> None:
    headers = """\
Received: from postal2.hspcopen.com by mail_app1; Wed, 18 Mar 2026 22:13:52 +0800 (CST)
发件人: "process.manuscript@hspcprocess.net" <process.manuscript@hspcprocess.net>
收件人: gaof57@mail.sysu.edu.cn
主题: Request for review of the manuscript - JCN0256
日期: 2026年3月18日 GMT+8 22:13:24
Message-Id: <94244875100002678131671@DESKTOP-6HKM3HO>
"""

    metadata = apple_apps.extract_header_metadata(headers)

    assert metadata["subject"] == "Request for review of the manuscript - JCN0256"
    assert metadata["sender"] == '"process.manuscript@hspcprocess.net" <process.manuscript@hspcprocess.net>'
    assert metadata["headerDate"] == "2026年3月18日 GMT+8 22:13:24"
    assert metadata["headerDateIso"] == "2026-03-18T22:13:24+08:00"
    assert metadata["dateSource"] == "日期"


def test_extract_header_metadata_falls_back_to_received_date() -> None:
    headers = """\
Delivered-To: gaofeng21cn@gmail.com
Received: by 2002:a17:907:789:b0:b94:1968:6c2d with SMTP id xd9csp5029216ejb; Tue, 17 Mar 2026 01:30:42 -0700 (PDT)
From: Google <no-reply@accounts.google.com>
Subject: 安全提醒
"""

    metadata = apple_apps.extract_header_metadata(headers)

    assert metadata["subject"] == "安全提醒"
    assert metadata["sender"] == "Google <no-reply@accounts.google.com>"
    assert metadata["headerDate"] == "Tue, 17 Mar 2026 01:30:42 -0700 (PDT)"
    assert metadata["headerDateIso"] == "2026-03-17T01:30:42-07:00"
    assert metadata["dateSource"] == "Received"


def test_build_triage_meta_item_uses_header_metadata() -> None:
    row = {
        "id": 142558,
        "messageId": "94244875100002678131671@DESKTOP-6HKM3HO",
        "subject": "Request for review of the manuscript - JCN0256",
        "sender": '"process.manuscript@hspcprocess.net" <process.manuscript@hspcprocess.net>',
        "read": False,
        "mailbox": "INBOX",
        "mailboxPath": "INBOX",
        "account": "SYSU",
    }
    headers = """\
Received: from postal2.hspcopen.com by mail_app1; Wed, 18 Mar 2026 22:13:52 +0800 (CST)
发件人: "process.manuscript@hspcprocess.net" <process.manuscript@hspcprocess.net>
主题: Request for review of the manuscript - JCN0256
日期: 2026年3月18日 GMT+8 22:13:24
"""

    item = apple_apps.build_triage_meta_item(row, headers)

    assert item == {
        "id": 142558,
        "messageId": "94244875100002678131671@DESKTOP-6HKM3HO",
        "subject": "Request for review of the manuscript - JCN0256",
        "sender": '"process.manuscript@hspcprocess.net" <process.manuscript@hspcprocess.net>',
        "read": False,
        "mailbox": "INBOX",
        "mailboxPath": "INBOX",
        "account": "SYSU",
        "headerDate": "2026年3月18日 GMT+8 22:13:24",
        "headerDateIso": "2026-03-18T22:13:24+08:00",
        "dateSource": "日期",
    }


def test_filter_triage_items_by_date_and_read_status() -> None:
    items = [
        {"id": 1, "read": False, "headerDateIso": "2026-03-18T22:13:24+08:00"},
        {"id": 2, "read": True, "headerDateIso": "2026-03-18T10:27:01+08:00"},
        {"id": 3, "read": False, "headerDateIso": "2026-03-17T16:30:41+08:00"},
    ]

    filtered = apple_apps.filter_triage_items(items, on_date="2026-03-18", include_read=False)

    assert [item["id"] for item in filtered] == [1]


def test_build_parser_supports_triage_meta_command() -> None:
    parser = apple_apps.build_parser()

    args = parser.parse_args(
        [
            "mail",
            "triage-meta",
            "--account",
            "SYSU",
            "--mailbox-path",
            "INBOX",
            "--limit",
            "5",
            "--on-date",
            "2026-03-18",
        ]
    )

    assert args.mail_action == "triage-meta"
    assert args.account == "SYSU"
    assert args.mailbox_path == "INBOX"
    assert args.limit == 5
    assert args.on_date == "2026-03-18"


def test_parse_recent_rows_output_parses_batch_applescript_rows() -> None:
    output = (
        "142558\t<root-1@example.com>\tProject Phoenix kickoff\t"
        "Alice <alice@example.com>\tfalse\tINBOX\tSYSU\t2026-03-20T09:00:00\t2026-03-20T08:58:00\n"
        "142559\t<reply-2@example.com>\tRe: Project Phoenix kickoff\t"
        "Bob <bob@example.com>\ttrue\tINBOX\tSYSU\t\t2026-03-20T10:00:00"
    )

    rows = apple_apps.parse_recent_rows_output(output)

    assert rows == [
        {
            "id": 142558,
            "messageId": "<root-1@example.com>",
            "subject": "Project Phoenix kickoff",
            "sender": "Alice <alice@example.com>",
            "read": False,
            "mailbox": "INBOX",
            "mailboxPath": "INBOX",
            "account": "SYSU",
            "dateReceived": "2026-03-20T09:00:00",
            "dateSent": "2026-03-20T08:58:00",
        },
        {
            "id": 142559,
            "messageId": "<reply-2@example.com>",
            "subject": "Re: Project Phoenix kickoff",
            "sender": "Bob <bob@example.com>",
            "read": True,
            "mailbox": "INBOX",
            "mailboxPath": "INBOX",
            "account": "SYSU",
            "dateReceived": None,
            "dateSent": "2026-03-20T10:00:00",
        },
    ]


def test_extract_thread_metadata_from_headers() -> None:
    row = {
        "messageId": "reply-2@example.com",
        "subject": "Re: Project Phoenix kickoff",
        "sender": "Alice <alice@example.com>",
    }
    headers = """\
Message-Id: <reply-2@example.com>
In-Reply-To: <root-1@example.com>
References: <root-1@example.com> <reply-1@example.com>
To: Bob <bob@example.com>
Subject: Re: Project Phoenix kickoff
"""

    metadata = apple_apps.extract_thread_metadata(row, headers)

    assert metadata["messageId"] == "<reply-2@example.com>"
    assert metadata["inReplyTo"] == "<root-1@example.com>"
    assert metadata["references"] == ["<root-1@example.com>", "<reply-1@example.com>"]
    assert metadata["subjectBase"] == "project phoenix kickoff"
    assert metadata["to"] == "Bob <bob@example.com>"


def test_search_meta_items_returns_direct_matches_and_thread_context() -> None:
    items = [
        {
            "id": 1,
            "subject": "Project Phoenix kickoff",
            "sender": "Alice <alice@example.com>",
            "messageId": "<root-1@example.com>",
            "inReplyTo": None,
            "references": [],
            "subjectBase": "project phoenix kickoff",
            "headerDateIso": "2026-03-20T09:00:00+08:00",
        },
        {
            "id": 2,
            "subject": "Re: Project Phoenix kickoff",
            "sender": "Bob <bob@example.com>",
            "messageId": "<reply-2@example.com>",
            "inReplyTo": "<root-1@example.com>",
            "references": ["<root-1@example.com>"],
            "subjectBase": "project phoenix kickoff",
            "headerDateIso": "2026-03-20T10:00:00+08:00",
        },
        {
            "id": 3,
            "subject": "Budget update",
            "sender": "Carol <carol@example.com>",
            "messageId": "<other-3@example.com>",
            "inReplyTo": None,
            "references": [],
            "subjectBase": "budget update",
            "headerDateIso": "2026-03-20T11:00:00+08:00",
        },
    ]

    results = apple_apps.search_meta_items(items, query="bob@example.com", limit=10)

    assert [item["id"] for item in results] == [2, 1]
    assert results[0]["matchType"] == "direct"
    assert results[1]["matchType"] == "thread"


def test_search_meta_items_treats_body_hits_as_direct_matches() -> None:
    items = [
        {
            "id": 10,
            "subject": "Weekly sync",
            "sender": "Alice <alice@example.com>",
            "messageId": "<weekly-root@example.com>",
            "inReplyTo": None,
            "references": [],
            "subjectBase": "weekly sync",
            "headerDateIso": "2026-03-20T09:00:00+08:00",
            "bodyHit": True,
        },
        {
            "id": 11,
            "subject": "Re: Weekly sync",
            "sender": "Bob <bob@example.com>",
            "messageId": "<weekly-reply@example.com>",
            "inReplyTo": "<weekly-root@example.com>",
            "references": ["<weekly-root@example.com>"],
            "subjectBase": "weekly sync",
            "headerDateIso": "2026-03-20T10:00:00+08:00",
        },
    ]

    results = apple_apps.search_meta_items(items, query="rare phrase in body", limit=10)

    assert [item["id"] for item in results] == [10, 11]
    assert results[0]["matchType"] == "direct"
    assert results[1]["matchType"] == "thread"


def test_find_body_hit_ids_batched_stops_after_hit_batch(monkeypatch) -> None:
    calls: list[list[int]] = []

    def fake_inline_bodies_for_messages(account: str, mailbox: str, message_ids: list[int]) -> list[dict]:
        calls.append(message_ids)
        return [
            {
                "id": message_id,
                "content": "Beta view is ready" if message_id == 3 else "nothing relevant here",
            }
            for message_id in message_ids
        ]

    monkeypatch.setattr(apple_apps, "inline_bodies_for_messages", fake_inline_bodies_for_messages)

    hits = apple_apps.find_body_hit_ids_batched(
        "SYSU",
        "INBOX",
        [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}],
        "Beta view",
        max_hits=1,
        batch_size=2,
    )

    assert hits == {3}
    assert calls == [[1, 2], [3, 4]]


def test_extract_header_metadata_decodes_rfc2047_and_folded_headers() -> None:
    headers = (
        "Received: from mx.example.test by mail.example.test;\r\n"
        " Thu, 19 Mar 2026 09:15:30 +0800\r\n"
        "From: =?UTF-8?B?5byg5LiJ?= <zhang@example.test>\r\n"
        "Subject: =?UTF-8?B?5rWL6K+V5Li76aKY?=\r\n"
        " =?UTF-8?Q?_Part_2?=\r\n"
        "Message-Id: <folded-1@example.test>\r\n"
        "References: <root@example.test>\r\n"
        " <mid@example.test>\r\n"
    )

    metadata = apple_apps.extract_header_metadata(headers)
    thread = apple_apps.extract_thread_metadata({}, headers)

    assert metadata["sender"] == "张三 <zhang@example.test>"
    assert metadata["subject"] == "测试主题 Part 2"
    assert metadata["headerDateIso"] == "2026-03-19T09:15:30+08:00"
    assert metadata["dateSource"] == "Received"
    assert thread["messageId"] == "<folded-1@example.test>"
    assert thread["references"] == ["<root@example.test>", "<mid@example.test>"]


def test_dispatch_delegates_to_opl_relay_and_falls_back_to_mail_app(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs):
        calls.append(cmd)
        if cmd[0] == "/usr/local/bin/opl-relay":
            if "accounts" in cmd:
                return type("R", (), {"returncode": 0, "stdout": '{"ok": true, "accounts": [{"name": "Work"}]}', "stderr": ""})()
            if "search" in cmd:
                return type("R", (), {"returncode": 0, "stdout": '{"ok": true, "messages": [{"storage_ref": "email-store://work/INBOX/1/abc"}]}', "stderr": ""})()
            return type("R", (), {"returncode": 2, "stdout": "", "stderr": "unsupported"})()
        raise AssertionError(f"unexpected command {cmd}")

    monkeypatch.setattr(apple_apps, "resolve_opl_relay_bin", lambda: "/usr/local/bin/opl-relay")
    monkeypatch.setattr(apple_apps.subprocess, "run", fake_run)

    accounts = apple_apps.dispatch_mail_action("accounts", {}, backend="auto")
    assert accounts == [{"name": "Work"}]
    assert calls[-1] == ["/usr/local/bin/opl-relay", "--json", "apple-mail", "accounts"]

    searched = apple_apps.dispatch_mail_action("search", {"query": "invoice", "limit": 5}, backend="opl-relay")
    assert searched == [{"storage_ref": "email-store://work/INBOX/1/abc"}]

    fallback_called: list[tuple[str, dict]] = []
    monkeypatch.setattr(apple_apps, "run_mail", lambda action, payload: fallback_called.append((action, payload)) or {"id": 9, "subject": "Fallback"})
    read_result = apple_apps.dispatch_mail_action("read", {"account": "Work", "mailboxPath": "INBOX", "id": "9"}, backend="auto")
    assert read_result == {"id": 9, "subject": "Fallback"}
    assert fallback_called == [("read", {"account": "Work", "mailboxPath": "INBOX", "id": "9"})]


def test_dispatch_delegates_to_himalaya_when_selected(monkeypatch) -> None:
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **_kwargs):
        captured.append(cmd)
        return type("R", (), {"returncode": 0, "stdout": '[{"id": "10", "subject": "Himalaya hit"}]', "stderr": ""})()

    monkeypatch.setattr(apple_apps, "resolve_himalaya_bin", lambda: "/opt/homebrew/bin/himalaya")
    monkeypatch.setattr(apple_apps.subprocess, "run", fake_run)

    result = apple_apps.dispatch_mail_action("search", {"account": "work", "query": "invoice", "limit": 5}, backend="himalaya")
    assert result == [{"id": "10", "subject": "Himalaya hit"}]
    assert captured == [["/opt/homebrew/bin/himalaya", "--output", "json", "envelope", "list", "--account", "work", "--page-size", "5", "invoice"]]
