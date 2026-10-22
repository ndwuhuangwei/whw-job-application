"""Integration checks using real Bash and XeLaTeX; no simulated compiler."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASH = os.environ.get('BASH_EXECUTABLE') or shutil.which('bash')
AVAILABLE = bool(BASH and shutil.which('xelatex'))


@unittest.skipUnless(AVAILABLE, 'Real Bash and XeLaTeX are required')
class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='resume-build-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / '版本 with spaces' / 'src'
        self.src.mkdir(parents=True)
        for name in ('build.sh', 'resume.tex'):
            shutil.copyfile(ROOT / 'assets' / 'latex' / name, self.src / name)

    def run_build(self, *args):
        return subprocess.run(
            [BASH, (self.src / 'build.sh').as_posix(), *args],
            cwd=self.root, capture_output=True, timeout=90,
        )

    def assert_pdf(self, path):
        self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
        self.assertGreater(path.stat().st_size, 1000)

    def test_default_build_from_different_working_directory(self):
        result = self.run_build()
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assert_pdf(self.src.parent / 'resume.pdf')
        self.assertFalse(list(self.src.glob('.build.*')))

    def test_explicit_unicode_names_and_failed_build_preserves_pdf(self):
        source = self.src / '自定义 简历.tex'
        (self.src / 'resume.tex').rename(source)
        result = self.run_build(source.name, '简历-示例.pdf')
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        target = self.src.parent / '简历-示例.pdf'
        self.assert_pdf(target)
        original = target.read_bytes()
        source.write_text('\\documentclass{article}\n\\begin{document}\n\\UndefinedCommand\n\\end{document}', encoding='utf-8')
        failed = self.run_build(source.name, target.name)
        self.assertNotEqual(failed.returncode, 0)
        self.assertEqual(target.read_bytes(), original)
        self.assertTrue(list(self.src.glob('.build.*/pass-1.txt')))

    def test_ambiguous_main_and_invalid_output_rejected(self):
        (self.src / 'resume.tex').rename(self.src / 'one.tex')
        shutil.copyfile(self.src / 'one.tex', self.src / 'two.tex')
        self.assertEqual(self.run_build().returncode, 2)
        self.assertEqual(self.run_build('one.tex', '../outside.pdf').returncode, 2)
        self.assertEqual(self.run_build('missing.tex').returncode, 2)
        self.assertFalse(list(self.root.rglob('*.pdf')))


if __name__ == '__main__':
    unittest.main()
