"""Exercise real helper CLIs and their content/integrity boundaries."""

from pathlib import Path
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("disk_steward_verify", SKILL / "scripts/verify_copy.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class HelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="disk-steward-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cli(self, name, *args, success=True):
        result = subprocess.run([sys.executable, str(SKILL / "scripts" / name), *map(str, args)],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def fixture(self):
        source = self.root / "source"
        source.mkdir()
        (source / "子目录").mkdir()
        (source / "子目录/正文.txt").write_text("Content 内容\n", encoding="utf-8")
        (source / "空 格\n换行.bin").write_bytes(bytes(range(256)) * 64)
        (source / "empty").write_bytes(b"")
        os.link(source / "empty", source / "hardlink")
        (source / "link").symlink_to("子目录/正文.txt")
        manifest = self.root / "manifest.json"
        self.cli("verify_copy.py", "manifest", source, "--output", manifest)
        return source, manifest

    def test_tree_and_tar_preserve_content_and_links(self):
        source, manifest = self.fixture()
        target = self.root / "copy"
        shutil.copytree(source, target, symlinks=True)
        self.cli("verify_copy.py", "tree", manifest, target)
        self.assertTrue((target / "link").is_symlink())
        archive = self.root / "copy.tar.gz"
        with tarfile.open(archive, "w:gz") as out:
            out.add(source, arcname=".")
        data = json.loads(self.cli("verify_copy.py", "tar", manifest, archive).stdout)
        self.assertEqual(data["status"], "verified_content")
        self.assertEqual(data["entries"], 6)

    def test_tree_rejects_equal_size_corruption_missing_and_extra(self):
        source, manifest = self.fixture()
        target = self.root / "copy"
        shutil.copytree(source, target, symlinks=True)
        payload = (target / "子目录/正文.txt").read_bytes()
        (target / "子目录/正文.txt").write_bytes(b"x" * len(payload))
        self.cli("verify_copy.py", "tree", manifest, target, success=False)
        (target / "子目录/正文.txt").write_bytes(payload)
        (target / "extra").touch()
        self.cli("verify_copy.py", "tree", manifest, target, success=False)
        (target / "extra").unlink()
        (target / "empty").unlink()
        self.cli("verify_copy.py", "tree", manifest, target, success=False)

    def test_symlink_target_is_compared_without_dereferencing(self):
        source, manifest = self.fixture()
        target = self.root / "copy"
        shutil.copytree(source, target, symlinks=True)
        (target / "link").unlink()
        (target / "link").symlink_to("../absent-private-content")
        self.cli("verify_copy.py", "tree", manifest, target, success=False)
        self.assertFalse((self.root / "absent-private-content").exists())

    def test_tar_rejects_unsafe_paths_and_duplicate_members(self):
        _, manifest = self.fixture()
        archive = self.root / "bad.tar"
        for names in [("../escape",), ("empty", "empty")]:
            with self.subTest(names=names):
                with tarfile.open(archive, "w") as out:
                    for name in names:
                        out.addfile(tarfile.TarInfo(name), io.BytesIO(b""))
                self.cli("verify_copy.py", "tar", manifest, archive, success=False)
                self.assertFalse((self.root / "escape").exists())

    def test_special_files_and_evidence_overwrite_are_rejected(self):
        source, manifest = self.fixture()
        os.mkfifo(source / "pipe")
        self.cli("verify_copy.py", "manifest", source, "--output", self.root / "new.json", success=False)
        (source / "pipe").unlink()
        old = manifest.read_bytes()
        self.cli("verify_copy.py", "manifest", source, "--output", manifest, success=False)
        self.assertEqual(manifest.read_bytes(), old)
        self.cli("verify_copy.py", "manifest", source, "--output", source / "inside.json", success=False)

    def test_placeholder_and_cross_volume_entry_are_not_opened(self):
        source = self.root / "source"
        source.mkdir()
        child = source / "payload"
        child.write_bytes(b"local-data")
        real_lstat = Path.lstat
        for field, value in [("st_flags", VERIFY.DATALESS), ("st_dev", -1)]:
            def fake_lstat(path):
                actual = real_lstat(path)
                if path == child:
                    data = {k: getattr(actual, k) for k in dir(actual) if k.startswith("st_")}
                    data[field] = value
                    return SimpleNamespace(**data)
                return actual
            with self.subTest(field=field), mock.patch.object(Path, "lstat", fake_lstat):
                with mock.patch.object(VERIFY.os, "open") as opener:
                    with self.assertRaises(ValueError):
                        VERIFY.inventory(source)
                    opener.assert_not_called()

    def test_content_changed_during_read_is_rejected(self):
        source = self.root / "source"
        source.mkdir()
        child = source / "payload"
        child.write_bytes(b"before")
        original = VERIFY.digest
        def mutate(stream):
            value = original(stream)
            child.write_bytes(b"after-and-longer")
            return value
        with mock.patch.object(VERIFY, "digest", side_effect=mutate):
            with self.assertRaises(ValueError):
                VERIFY.inventory(source)

    def baseline(self):
        return {"schema": "mac_disk_baseline/v1", "host": "fixture-host",
                "captured_at": "2026-01-01T00:00:00+00:00", "volume": {"uuid": "fixture-volume"},
                "filesystem_space": {"available_bytes": 1000},
                "roots": [{"path": "fixture/root", "status": "ok", "allocated_bytes": 100},
                          {"path": "fixture/unknown", "status": "error"}],
                "measurement_note": "Independent directory allocations are not additive."}

    def test_baseline_comparison_preserves_unknown_and_separate_accounting(self):
        before, after = self.root / "before.json", self.root / "after.json"
        a = self.baseline()
        before.write_text(json.dumps(a))
        a["filesystem_space"]["available_bytes"] = 1300
        a["roots"][0]["allocated_bytes"] = 80
        after.write_text(json.dumps(a))
        data = json.loads(self.cli("disk_baseline.py", "compare", before, after).stdout)
        self.assertEqual(data["filesystem_space"]["net_available_increase_bytes"], 300)
        self.assertEqual(data["roots"][0]["allocated_increase_bytes"], -20)
        self.assertEqual(data["roots"][1]["status"], "not_comparable")
        self.assertNotIn("allocated_increase_bytes", data["roots"][1])

    def test_baseline_rejects_different_identity_and_preserves_existing_output(self):
        before, after = self.root / "before.json", self.root / "after.json"
        before.write_text(json.dumps(self.baseline()))
        for field in ("host", "volume"):
            a = self.baseline()
            a[field] = "other" if field == "host" else {"uuid": "other"}
            after.write_text(json.dumps(a))
            self.cli("disk_baseline.py", "compare", before, after, success=False)
        after.write_text(before.read_text())
        old = after.read_bytes()
        self.cli("disk_baseline.py", "compare", before, after, "--output", after, success=False)
        self.assertEqual(after.read_bytes(), old)

    @unittest.skipUnless(sys.platform == "darwin", "Real volume capture requires macOS")
    def test_actual_macos_capture(self):
        source = self.root / "source"
        source.mkdir()
        (source / "payload").write_bytes(b"x" * 8192)
        report = self.root / "baseline.json"
        self.cli("disk_baseline.py", "capture", "--root", source, "--output", report)
        data = json.loads(report.read_text())
        self.assertTrue(data["volume"]["uuid"])
        self.assertEqual(data["roots"][0]["status"], "ok")
        self.assertGreaterEqual(data["roots"][0]["allocated_bytes"], 8192)


if __name__ == "__main__":
    unittest.main()
