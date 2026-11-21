---
name: xiaohongshu-repo-scout
description: Use when turning XiaoHongShu or Chinese social-media posts into a verified GitHub repository shortlist, especially for academic, research, AI, data, visualization, writing, or automation tools. Use when the user asks to find repos from XiaoHongShu posts, compare social recommendations against GitHub evidence, check repo stars/freshness from post leads, or confirm whether an OpenCLI/Agent Reach XiaoHongShu lead is actionable. Not for generic web research, posting/publishing, social engagement growth, or repo evaluation without a social-source lead.
---

# XiaoHongShu Repo Scout

## Overview

Use this skill to convert social discovery into a defensible GitHub shortlist. Social engagement is only a lead source; a repository becomes a candidate only after exact identity extraction and fresh GitHub verification.

This skill complements `agent-reach`: use `agent-reach` or OpenCLI to fetch XiaoHongShu content, then apply this workflow to avoid guessing repo identities or treating post popularity as quality evidence.

## Evidence Order

1. Use the user's selected read route. For Agent Reach, `agent-reach channels` lists the XiaoHongShu actions supported by the installed CLI. Search for a domain and repository together:

```bash
agent-reach xiaohongshu search "<query>" --limit 5
```

2. Read a promising note with its complete URL from the search response, including the access query when present:

```bash
agent-reach xiaohongshu read "<full-search-result-url>"
```

   Check the returned note text for an identifiable repository. A public-web snippet can yield a lead. Record it as a snippet until the note body is available. If the route reports a login requirement, rate limit or platform block, keep the evidence already obtained and report the gap.

3. For a selected OpenCLI route, use `opencli xiaohongshu search "<query>" -f json` followed by `opencli xiaohongshu note "<full-search-result-url>" -f json`. OpenCLI 2 wraps rows in `{ok, data}`. Inspect the field/value rows under `data`; a successful response with an empty list supplies no note. Keep access parameters in the read request only. Cite the title or a public note permalink in reports. [Agent Reach v1.6.1](https://github.com/Panniantong/Agent-Reach/releases/tag/v1.6.1) · [OpenCLI response handling](https://github.com/Panniantong/Agent-Reach/commit/387b2b7)

4. Extract only explicit repository identities:
   - Direct GitHub URLs.
   - Owner/repo strings.
   - Unique project names that can be matched by fresh GitHub search.
   - Exclude posts that only imply a tool, show screenshots, or use vague names without a stable repo identity.

5. Verify each candidate with GitHub:

```bash
gh repo view <owner>/<repo> --json nameWithOwner,description,stargazerCount,forkCount,pushedAt,latestRelease,url,isArchived,defaultBranchRef
gh search repos "<project name>" --sort stars --limit 10
```

Use the latest release tag and publication date for what users can install. For default-branch activity, read its latest commit and date when that matters. Repository-wide `pushedAt` can reflect another branch. A repository with no GitHub Release may publish through a package registry or tags. If GitHub API rate limiting blocks verification, report that as a verification gap and do not claim current stars or freshness.

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
- Source lead: XiaoHongShu query, note title, or public permalink with access parameters removed.
- Confidence: high / medium / low.
- Caveat or next check if the repo should be tried before adoption.

Also include a short rejected/uncertain list when useful, especially for high-engagement posts that failed repo identity or GitHub verification.

## Safety Boundaries

- Do not publish, delete, follow, unfollow, like, or comment on XiaoHongShu unless the user explicitly asks and confirms the exact write action.
- Treat OpenCLI XiaoHongShu write commands as browser UI automation, not stable official APIs.
- Prefer drafting copy or preparing a confirmation prompt over unattended posting.
- Do not claim Agent Reach or OpenCLI is fully healthy from `doctor` alone; prove the actual channel with a real search/note read.
