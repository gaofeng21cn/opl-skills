# OPL Skills

Independently useful public Codex workflows maintained by `gaofeng21cn`. The
canonical repository is `gaofeng21cn/opl-skills`.

## Repository Role

OPL-owned software-development Skills live in the OPL Flow Plugin and share one
installation and update lifecycle. This repository keeps only reusable
non-development workflows that remain useful without OPL Flow.

The [Skill catalog](contracts/skill-catalog.json) owns the current identities,
source paths, and categories. Individual `SKILL.md` files own their workflow
instructions and load supporting references only for that subject.

Personal Skills belong in the owner's private OPL Instance. OpenAI and
third-party Skills are installed and updated through their native owner channel;
this repository does not copy them.

## Catalog

[`contracts/skill-catalog.json`](contracts/skill-catalog.json) maps each current
Skill ID to its source path and browsing category. Categories never install
Skills. There are no presets or wildcard installation rules.

## Install

Install only the requested Skill IDs with the bundled Codex installer:

```bash
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo gaofeng21cn/opl-skills \
  --path skills/<skill-name>
```

The private OPL Instance may record an explicit desired inventory for multiple
machines. Each node still installs from this owner; Fleet reports presence and
does not copy Skill bytes between machines.

## Development

```bash
python scripts/validate_skills.py
python -m unittest tests/test_validate_skill_catalog.py
pytest skills/apple-mail/tests/test_mail_meta.py -q
```

Each Skill must remain independently installable. Public source must not contain
credentials, machine inventories, private remotes, or absolute personal paths.

Update a workflow's instructions together with its helper or source contract.
Keep one owner for each procedure; link to another Skill instead of copying its
implementation or routing policy. Replace superseded advice in place and keep
completed history in Git. Retiring a workflow removes its catalog entry,
payload, obsolete checks, and inbound references together after caller cutover;
do not preserve compatibility instructions in active Skills.
