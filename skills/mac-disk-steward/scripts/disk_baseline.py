#!/usr/bin/env python3
"""只读采集Mac空间基线，或比较同一设备/卷的两份基线。"""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys

SCHEMA = "mac_disk_baseline/v1"


def command(argv, timeout=15):
    try:
        p = subprocess.run(argv, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"status": "error", "error": str(exc)}, None
    if p.returncode:
        return {"status": "error", "returncode": p.returncode,
                "error": p.stderr.decode(errors="replace")[:600]}, None
    return {"status": "ok"}, p.stdout


def disk_info(path):
    result, raw = command(["diskutil", "info", "-plist", str(path)])
    if raw is None:
        raise ValueError("无法确认本地卷身份：" + str(result))
    data = plistlib.loads(raw)
    if not data.get("VolumeUUID") or not data.get("MountPoint"):
        raise ValueError("目标缺少卷UUID或挂载信息")
    return data


def capture(args):
    if sys.platform != "darwin":
        raise ValueError("capture需要macOS；compare可离线运行")
    volume = Path(args.volume).expanduser().absolute()
    info = disk_info(volume)
    space = shutil.disk_usage(volume)
    data = {
        "schema": SCHEMA,
        "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "host": platform.node(),
        "volume": {"path": str(volume), "uuid": info["VolumeUUID"],
                   "mount_point": info["MountPoint"],
                   "device": info.get("DeviceIdentifier"),
                   "filesystem": info.get("FilesystemType"),
                   "container": info.get("APFSContainerReference")},
        "filesystem_space": {"total_bytes": space.total, "used_bytes": space.used,
                             "available_bytes": space.free},
        "roots": [],
    }
    status, raw = command(["diskutil", "apfs", "list", "-plist"])
    if raw:
        containers = plistlib.loads(raw).get("Containers", [])
        for c in containers:
            if c.get("ContainerReference") == data["volume"]["container"]:
                data["apfs_container_space"] = {
                    "uuid": c.get("APFSContainerUUID"),
                    "total_bytes": c["CapacityCeiling"],
                    "available_bytes": c["CapacityFree"],
                    "used_bytes": c["CapacityCeiling"] - c["CapacityFree"],
                }
                break
    else:
        data["apfs_query"] = status
    volume_device = volume.stat().st_dev
    for raw_root in dict.fromkeys(args.root):
        root = Path(raw_root).expanduser().absolute()
        row = {"path": str(root)}
        try:
            if root.is_symlink() or not root.is_dir():
                raise ValueError("仅扫描显式本地目录，拒绝根软链接或非目录")
            if root.stat().st_dev != volume_device:
                raise ValueError("目录与基线卷不在同一文件系统；远程/其他卷单独评估")
            result, raw = command(["du", "-skx", str(root)], args.timeout)
            row.update(result)
            if raw is not None:
                row["allocated_bytes"] = int(raw.split(None, 1)[0]) * 1024
        except (OSError, ValueError) as exc:
            row.update(status="error", error=str(exc))
        data["roots"].append(row)
    data["time_machine"] = {}
    for key, argv in [
        ("snapshots", ["tmutil", "listlocalsnapshots", info["MountPoint"]]),
        ("status", ["tmutil", "status"]),
    ]:
        result, raw = command(argv)
        if raw is not None:
            result["output"] = raw.decode(errors="replace").strip()
        data["time_machine"][key] = result
    data["measurement_note"] = (
        "字节；目录为du分配量，可能嵌套/共享；不得与实际可用空间差额相加。"
        "本脚本不判定可删，不读取文件正文。"
    )
    data["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    return data


def compare(args):
    old, new = [json.loads(Path(p).read_text()) for p in (args.before, args.after)]
    if old.get("schema") != SCHEMA or new.get("schema") != SCHEMA:
        raise ValueError("基线schema不匹配")
    for key in ("host",):
        if not old.get(key) or old[key] != new.get(key):
            raise ValueError("设备身份不同或未知，拒绝比较")
    if not old["volume"].get("uuid") or old["volume"]["uuid"] != new["volume"].get("uuid"):
        raise ValueError("卷UUID不同或未知，拒绝比较")
    result = {"schema": "mac_disk_comparison/v1", "host": new["host"],
              "volume_uuid": new["volume"]["uuid"],
              "before_at": old["captured_at"], "after_at": new["captured_at"],
              "roots": [], "measurement_note": new["measurement_note"]}
    for field in ("filesystem_space", "apfs_container_space"):
        a, b = old.get(field), new.get(field)
        if not a or not b:
            continue
        if a.get("uuid") != b.get("uuid"):
            raise ValueError("APFS容器身份不同，拒绝比较")
        result[field] = {"before_available_bytes": a["available_bytes"],
                         "after_available_bytes": b["available_bytes"],
                         "net_available_increase_bytes": b["available_bytes"] - a["available_bytes"]}
    before = {r["path"]: r for r in old["roots"]}
    after = {r["path"]: r for r in new["roots"]}
    for path in sorted(before.keys() | after.keys()):
        a, b = before.get(path), after.get(path)
        row = {"path": path, "status": "not_comparable"}
        if a and b and a["status"] == b["status"] == "ok":
            row.update(status="ok", before_allocated_bytes=a["allocated_bytes"],
                       after_allocated_bytes=b["allocated_bytes"],
                       allocated_increase_bytes=b["allocated_bytes"] - a["allocated_bytes"])
        result["roots"].append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    cap = sub.add_parser("capture", help="只读空间、目录元数据及快照状态")
    cap.add_argument("--volume", default="/System/Volumes/Data")
    cap.add_argument("--root", action="append", default=[], help="已确认的本地目录；可重复")
    cap.add_argument("--timeout", type=int, default=60, help="每个du扫描秒数，默认60")
    cap.add_argument("--output", type=Path)
    diff = sub.add_parser("compare", help="同设备同卷基线比较")
    diff.add_argument("before")
    diff.add_argument("after")
    diff.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if getattr(args, "timeout", 1) <= 0:
            raise ValueError("timeout必须为正数")
        if args.output and args.output.exists():
            raise ValueError("输出已存在，换用新检查点文件")
        data = capture(args) if args.mode == "capture" else compare(args)
        content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            with args.output.open("x", encoding="utf-8") as out:
                out.write(content)
            print(json.dumps({"status": "recorded", "output": str(args.output)}, ensure_ascii=False))
        else:
            print(content, end="")
    except (OSError, ValueError, KeyError, plistlib.InvalidFileException) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
