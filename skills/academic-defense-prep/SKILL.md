---
name: academic-defense-prep
description: Use when turning academic or medical-research materials into defense deliverables, including timed oral scripts, PPT speaker notes, narrative/storyline rewrites, reviewer-facing questions with background notes, or paired slide-notes plus script outputs. Trigger on PPT/PPTX plus source PDFs, thesis zip packages, proposal/application materials, dissertation defenses, project defenses, or requests such as “5分钟逐字稿”, “讲者备注”, “答辩问题”, “控制节奏”, or “叙事逻辑”. Pair with Office/PPTX/PDF extraction skills for file operations.
---

# Academic Defense Prep

## Overview

This skill turns real academic materials into evaluator-ready defense outputs. It focuses on pacing, storyline, reviewer identity, and source-grounded wording; it does not replace Office/PDF tools for low-level file extraction or editing.

## Evidence First

Before drafting:
- Read the current deck outline and visible slide text when a `.pptx` is provided.
- Extract or read backing PDFs, proposals, theses, abstracts, conclusions, and appendices that define the actual claims.
- For a zip of theses, extract text locally before writing questions; use abstracts/conclusions/results to map the topic.
- If the task involves editing speaker notes, inspect existing notes first and verify the final PPT package after editing.

Useful tool patterns:
- PPT structure: `officecli view <file.pptx> outline` and `officecli view <file.pptx> text`.
- PPT notes: `officecli query <file.pptx> notes`, `officecli help pptx notes`, `officecli set <file.pptx> '/slide[N]/notes' --prop text=...`.
- PDF text: prefer the configured PDF/MinerU workflow; `pdftotext -layout` is enough for many thesis PDFs.
- Integrity checks after PPT edits: `officecli validate <file.pptx>` and `unzip -t <file.pptx>`.

## Timed Defense Script

For requests like “5分钟逐字稿”:
- Produce a spoken script, not bullet notes.
- Compress slides into speaking blocks: key slides get full explanation; support slides are bridged quickly.
- Mark milestone times when requested, such as `0:00-0:40`, `1:05`, or “第 X 部分结束”.
- Keep a small buffer under the stated limit; a 5-minute defense should often target about 4:45-5:00.
- Preserve slide body/layout unless the user explicitly asks to rewrite the deck.

Default script shape:
- Opening: problem/context and project objective.
- Core: method/technical route, major work packages, evidence/results, and feasibility.
- Support: team, platform, papers, patents, funding, collaborations, or prior basis.
- Closing: expected contribution, next step, or approval/translation target.

## Storyline Rewrite

For “叙事逻辑” or reviewer-facing rewrite:
- Do not prescribe a fixed slide count unless asked.
- State the narrative arc and where existing materials should move conceptually.
- Preserve support sections that matter to credibility, such as research contents, AI+clinical+engineering team, papers, awards, IP, platform support, and prior clinical basis.
- For non-specialist reviewers, move from clinical pain point to why the current approach is insufficient, then to the proposed system, evidence, feasibility, team, and translation path.
- Use precise domain terminology once confirmed by the user or source material. In medical-device contexts, avoid vague “备案/条件” wording when formal approval language is needed.

## Speaker Notes Editing

When asked to update PPT speaker notes:
- Treat notes plus timed script as paired deliverables if both are requested.
- Keep each note aligned to the slide’s role in the oral flow, not a verbatim copy of slide bullets.
- Use `officecli add <deck> '/slide[N]' --type notes --prop text=...` when the slide has no notes part. Use `set` on `'/slide[N]/notes'` to replace existing notes. Read each changed slide's notes back against its script.
- With a resident open, run `officecli save <deck>` before reading the ZIP from another tool. After reordering slides, follow the presentation's slide relationships and each slide's notes relationship. The suffix on `notesSlideN.xml` can differ from the displayed slide number.
- If text still differs, inspect the notes shape with placeholder type `body`. Other shapes can contain a slide number, date, or footer. Preserve them during a repair and work on a copy if direct XML editing is needed. [OfficeCLI notes fix](https://github.com/iOfficeAI/OfficeCLI/commit/1cc86397b7f7eb253b90a249decc4b3adafe4bd8) · [OfficeCLI v1.0.163](https://github.com/iOfficeAI/OfficeCLI/releases/tag/v1.0.163)

## Defense Questions

For thesis or proposal review questions:
- Default to explanatory, constructive, non-hostile questions.
- For each student/project, usually provide 2 main questions plus at most one optional follow-up unless the user asks for more.
- Add a one-sentence background/rationale for each question so the evaluator can decide when to ask it.
- Shape questions to the user’s stated reviewer identity. For medicine-AI review, emphasize data leakage, prediction window, thresholding, interpretability, external validation, domain shift, batch effects, multimodal integration, and clinical deployment boundaries.

## Output Shapes

Timed script:
```markdown
0:00-0:35 开场与问题定义
...
4:35-4:55 收束
```

Storyline advice:
```markdown
主线：临床痛点 -> 现有方案边界 -> 本项目方案 -> 关键证据 -> 团队与转化路径
需要保留并前移的材料：...
需要弱化或后置的材料：...
```

Reviewer questions:
```markdown
学生 / 项目：...
1. 问题...
   背景：...
2. 问题...
   背景：...
可选追问：...
```

Notes-edit closeout:
- Files edited
- Verification commands and results
- Any slides with manual XML cleanup

## Stop Conditions

Pause and ask or report a blocker when:
- Required source files are missing or unreadable.
- The requested timing is incompatible with the amount of material and the user has forbidden compression.
- Editing the PPT would overwrite unrelated user changes or a package-level corruption cannot be verified.
- The user asks for exact current policy, regulatory, or submission wording that may have changed and no live source has been checked.

Do not invent results, publications, regulatory status, clinical claims, or authorship facts not supported by the provided materials.
