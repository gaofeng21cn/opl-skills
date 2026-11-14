#!/usr/bin/env python3
"""为冻结的普通文件树建立内容清单，回读副本树或tar归档；不删除或提取文件。"""

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile

SCHEMA = "mac_disk_content_manifest/v1"
DATALESS = getattr(stat, "UF_DATALESS", 0x40000000)


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
        h.update(block)
    return h.hexdigest()


def fingerprint(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def inventory(root):
    root = Path(root).expanduser().absolute()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("根必须是实际目录，不能为软链接")
    device = root.stat().st_dev
    entries = []

    def visit(path):
        before = path.lstat()
        if before.st_dev != device:
            raise ValueError("拒绝跨卷子树：" + str(path))
        if getattr(before, "st_flags", 0) & DATALESS:
            raise ValueError("拒绝读取云盘占位文件/目录：" + str(path))
        rel = path.relative_to(root).as_posix()
        record = {"path": rel}
        if stat.S_ISDIR(before.st_mode):
            if path != root:
                entries.append({**record, "type": "directory"})
            with os.scandir(path) as scan:
                names = sorted(item.name for item in scan)
            for name in names:
                visit(path / name)
        elif stat.S_ISREG(before.st_mode):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            fd = os.open(path, flags)
            with os.fdopen(fd, "rb") as stream:
                opened = os.fstat(stream.fileno())
                if fingerprint(opened) != fingerprint(before):
                    raise ValueError("打开时文件变化：" + str(path))
                record.update(type="file", bytes=before.st_size, sha256=digest(stream))
                if fingerprint(os.fstat(stream.fileno())) != fingerprint(before):
                    raise ValueError("读取时文件变化：" + str(path))
            entries.append(record)
        elif stat.S_ISLNK(before.st_mode):
            entries.append({**record, "type": "symlink", "target": os.readlink(path)})
        else:
            raise ValueError("不支持socket/FIFO/设备等特殊对象：" + str(path))
        if fingerprint(path.lstat()) != fingerprint(before):
            raise ValueError("扫描时对象变化：" + str(path))

    visit(root)
    return entries


def safe_name(value):
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or "\x00" in value:
        raise ValueError("拒绝不安全相对路径：" + repr(value))
    return p.as_posix()


def indexed(entries):
    result = {}
    for entry in entries:
        name = safe_name(entry["path"])
        if name == "." or name in result or entry["type"] not in ("file", "directory", "symlink"):
            raise ValueError("清单重复/无效成员：" + name)
        result[name] = entry
    return result


def check(expected, actual):
    if expected.keys() != actual.keys():
        raise ValueError(json.dumps({"missing_count": len(expected.keys() - actual.keys()),
                                    "extra_count": len(actual.keys() - expected.keys()),
                                    "missing_sample": sorted(expected.keys() - actual.keys())[:5],
                                    "extra_sample": sorted(actual.keys() - expected.keys())[:5]}, ensure_ascii=False))
    for path, wanted in expected.items():
        got = actual[path]
        fields = {"file": ("type", "bytes", "sha256"),
                  "symlink": ("type", "target"), "directory": ("type",)}[wanted["type"]]
        if any(wanted.get(k) != got.get(k) for k in fields):
            raise ValueError("内容或类型不同：" + path)


def archive_entries(path, expected):
    actual, links = {}, []
    with tarfile.open(path, "r|*") as archive:
        for member in archive:
            name = safe_name(member.name)
            if name == "." and member.isdir():
                continue
            if name in actual:
                raise ValueError("归档有重复成员：" + name)
            if name not in expected:
                raise ValueError("归档有额外成员：" + name)
            if member.isfile():
                with archive.extractfile(member) as stream:
                    actual[name] = {"type": "file", "bytes": member.size, "sha256": digest(stream)}
            elif member.isdir():
                actual[name] = {"type": "directory"}
            elif member.issym():
                actual[name] = {"type": "symlink", "target": member.linkname}
            elif member.islnk():
                actual[name] = {"type": "hardlink"}
                links.append((name, safe_name(member.linkname)))
            else:
                raise ValueError("归档含特殊对象：" + name)
    while links:
        unresolved = []
        for name, target in links:
            if actual.get(target, {}).get("type") == "file":
                actual[name] = actual[target].copy()
            else:
                unresolved.append((name, target))
        if len(unresolved) == len(links):
            raise ValueError("归档硬链接缺目标/成环：" + repr(unresolved[:3]))
        links = unresolved
    return actual


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    manifest = sub.add_parser("manifest", help="冻结普通文件树内容清单；不记录完整Mac元数据")
    manifest.add_argument("source", type=Path)
    manifest.add_argument("--output", type=Path, required=True)
    for name, help_text in [("tree", "校验解包/复制后的目录；不跟随软链接"),
                            ("tar", "流式读取tar/gzip/bzip2/xz；根布局应与清单相同")]:
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("manifest", type=Path)
        cmd.add_argument("target", type=Path)
        cmd.add_argument("--output", type=Path, help="可选校验结果文件，必须不存在")
    args = parser.parse_args()
    try:
        if args.output:
            if args.output.exists():
                raise ValueError("输出已存在")
            target_root = (args.source if args.mode == "manifest" else args.target).expanduser().resolve()
            if target_root.is_dir() and args.output.resolve().is_relative_to(target_root):
                raise ValueError("输出必须位于扫描目录之外，避免改变被验证集合")
        if args.mode == "manifest":
            entries = inventory(args.source)
            data = {"schema": SCHEMA, "source": str(args.source.expanduser().absolute()),
                    "created_at": dt.datetime.now(dt.timezone.utc).isoformat(), "entries": entries}
        else:
            data = json.loads(args.manifest.read_text())
            if data.get("schema") != SCHEMA:
                raise ValueError("清单schema不匹配")
            expected = indexed(data["entries"])
            actual = indexed(inventory(args.target)) if args.mode == "tree" else archive_entries(args.target, expected)
            check(expected, actual)
            data = {"status": "verified_content", "target": str(args.target),
                    "manifest": str(args.manifest), "entries": len(expected),
                    "payload_bytes": sum(x.get("bytes", 0) for x in expected.values()),
                    "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "coverage": "内容、结构及软链接文本；不证明ACL/扩展属性/外部链接目标或业务可用"}
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as out:
                out.write(content)
            print(json.dumps({"status": "recorded", "output": str(args.output)}, ensure_ascii=False))
        else:
            print(content, end="")
    except (OSError, ValueError, KeyError, tarfile.TarError, EOFError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
