"""Focused regression checks: stale versions, lost edits, missing files, no writes."""
from pathlib import Path
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resume_tools.py"
spec = importlib.util.spec_from_file_location("resume_tools", SCRIPT)
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class ResumeToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "已确认版" / "src" / "resume.tex"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("已确认的正文", encoding="utf-8")

    def test_catalog_excludes_stale_and_does_not_infer_confirmation(self):
        for folder in ["历史-stale", ".hidden", "qa"]:
            target = self.root / folder / "src" / "resume.tex"
            target.parent.mkdir(parents=True)
            target.write_text("ignored")
        (self.source.parent / "resume.pdf").write_bytes(b"compiled")
        official = self.source.parent.parent / "正式.pdf"
        official.write_bytes(b"official")
        rows = tools.catalog(self.root)["versions"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["pdfs"], [official.as_posix()])
        self.assertEqual(rows[0]["confirmation_status"], "requires_evidence")

    def test_same_length_edit_with_same_timestamp_is_detected(self):
        entry = tools.fingerprint(self.source)
        previous = self.source.stat()
        self.source.write_text("用户编辑正文", encoding="utf-8")
        os.utime(self.source, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        result = tools.verify({"artifacts": [entry]})
        self.assertFalse(result["unchanged"])
        self.assertEqual(result["artifacts"][0]["status"], "changed")

    def test_missing_artifact_not_reported_as_unchanged(self):
        entry = tools.fingerprint(self.source)
        self.source.unlink()
        self.assertEqual(tools.verify({"artifacts": [entry]})["artifacts"][0]["status"], "missing")

    def test_empty_malformed_relative_and_duplicate_records_rejected(self):
        entry = tools.fingerprint(self.source)
        for state in [
            {}, {"artifacts": []}, {"artifacts": [None]},
            {"artifacts": [{"path": "relative.tex", "sha256": "0" * 64}]},
            {"artifacts": [{"path": str(self.source), "sha256": "invalid"}]},
            {"artifacts": [entry, entry]},
        ]:
            with self.subTest(state=state), self.assertRaises(ValueError):
                tools.verify(state)

    def test_tools_leave_source_bytes_untouched(self):
        before = self.source.read_bytes()
        entry = tools.fingerprint(self.source)
        tools.catalog(self.root)
        result = tools.verify({"artifacts": [entry]})
        self.assertTrue(result["unchanged"])
        self.assertEqual(self.source.read_bytes(), before)

    def test_cli_handles_bom_unicode_and_change_exit_status(self):
        state = self.root / "状态.json"
        state.write_text(json.dumps({"artifacts": [tools.fingerprint(self.source)]}), encoding="utf-8-sig")
        command = [sys.executable, "-X", "utf8", str(SCRIPT), "verify", str(state)]
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
        self.source.write_text("changed", encoding="utf-8")
        changed = subprocess.run(command, capture_output=True)
        self.assertEqual(changed.returncode, 1)
        self.assertFalse(json.loads(changed.stdout)["unchanged"])
        state.write_text("{}", encoding="utf-8")
        self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)


if __name__ == "__main__":
    unittest.main()
