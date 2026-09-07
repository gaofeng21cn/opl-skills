---
name: xiaohongshu-repo-scout
description: Use when turning XiaoHongShu or Chinese social-media posts into a verified GitHub repository shortlist, especially for academic, research, AI, data, visualization, writing, or automation tools. Use when the user asks to find repos from XiaoHongShu posts, compare social recommendations against GitHub evidence, check repo stars/freshness from post leads, or confirm whether an OpenCLI/Agent Reach XiaoHongShu lead is actionable. Not for generic web research, posting/publishing, social engagement growth, or repo evaluation without a social-source lead.
---

# XiaoHongShu Repo Scout

## Overview

Use this skill to convert social discovery into a defensible GitHub shortlist. Social engagement is only a lead source; a repository becomes a candidate only after exact identity extraction and fresh GitHub verification.

This skill complements `agent-reach`: use `agent-reach` or OpenCLI to fetch XiaoHongShu content, then apply this workflow to avoid guessing repo identities or treating post popularity as quality evidence.

## Evidence Order

1. Check the active XiaoHongShu backend before reading:

```bash
agent-reach doctor --json
opencli daemon status
```

Use the backend established by the current readback; public workflow source
does not carry one machine's previous backend choice.

2. Search XiaoHongShu with a query that names the domain and repository/tool intent:

```bash
opencli xiaohongshu search "<query>" -f yaml
```

3. Read promising notes by passing the full search-result URL that includes `xsec_token`, not a bare note id:

```bash
opencli xiaohongshu note "<full-search-result-url-with-xsec-token>" -f yaml
```

If search works but note reads fail, first check whether the URL lost `xsec_token`.

4. Extract only explicit repository identities:
   - Direct GitHub URLs.
   - Owner/repo strings.
   - Unique project names that can be matched by fresh GitHub search.
   - Exclude posts that only imply a tool, show screenshots, or use vague names without a stable repo identity.

5. Verify each candidate with GitHub:

```bash
gh repo view <owner>/<repo> --json nameWithOwner,description,stargazerCount,forkCount,updatedAt,url,isArchived,defaultBranchRef
gh search repos "<project name>" --sort stars --limit 10
```

Use current GitHub evidence for stars, archive state, description, and update recency. If GitHub API rate limiting blocks verification, report that as a verification gap and do not claim current stars or freshness.

## Candidate Rules

Recommend a repository only when all are true:

- A XiaoHongShu/source note or search result produced the lead.
- The exact GitHub repo identity is confirmed.
- Fresh GitHub metadata was read in the current task.
- The repo's purpose matches the user's requested domain.
- Any safety or write-operation boundary is clear.

Skip or downgrade a repository when:

- The post has engagement but no exact repo identity.
- Multiple repos could match and none is clearly the one referenced.
- The repo is archived, stale, unrelated, low-signal, or mostly empty.
- Verification depends only on a social post, screenshot, README claim, or cached summary.

## Output Shape

Lead with the shortlist, then show why each item survived filtering.

For each recommended repo include:

- Repository name and URL.
- Why it is relevant to the user's requested workflow.
- Fresh stars and update signal from GitHub.
- Source lead: XiaoHongShu query/note title or URL when available.
- Confidence: high / medium / low.
- Caveat or next check if the repo should be tried before adoption.

Also include a short rejected/uncertain list when useful, especially for high-engagement posts that failed repo identity or GitHub verification.

## Safety Boundaries

- Do not publish, delete, follow, unfollow, like, or comment on XiaoHongShu unless the user explicitly asks and confirms the exact write action.
- Treat OpenCLI XiaoHongShu write commands as browser UI automation, not stable official APIs.
- Prefer drafting copy or preparing a confirmation prompt over unattended posting.
- Do not claim Agent Reach or OpenCLI is fully healthy from `doctor` alone; prove the actual channel with a real search/note read.
