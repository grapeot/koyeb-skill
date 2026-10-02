"""Offline credential and subprocess boundary tests; no cloud API calls."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "koyeb_env.py"
spec = importlib.util.spec_from_file_location("koyeb_env", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.file = self.root / ".env"
        self.file.write_text("KOYEB_API_KEY=replace-with-your-key\n")
        self.binary = self.root / "koyeb"
        self.binary.write_text(
            f"#!{sys.executable}\n"
            "import os,sys\n"
            "assert os.environ['KOYEB_TOKEN']==os.environ.get('EXPECTED_TOKEN','replace-with-your-key')\n"
            "assert 'KOYEB_API_KEY' not in os.environ\n"
            "assert os.environ['KOYEB_URL']=='https://app.koyeb.com'\n"
            "assert os.environ['KOYEB_TOKEN'] not in sys.argv\n"
            "print(' '.join(sys.argv[1:]))\n"
            "sys.exit(int(os.environ.get('CHILD_EXIT','0')))\n"
        )
        self.binary.chmod(0o755)
        self.env = os.environ.copy()
        self.env.update(KOYEB_TOKEN="stale-example-token", KOYEB_API_KEY="ambient-example-token", KOYEB_URL="https://example.com")
        self.env["PATH"] = str(self.root) + os.pathsep + self.env.get("PATH", "")

    def run_cli(self, *args, explicit=True):
        command = [sys.executable, str(SCRIPT)]
        if explicit:
            command += ["--env-file", str(self.file)]
        command += ["--koyeb-bin", str(self.binary), "--", *args]
        return subprocess.run(command, cwd=self.root, env=self.env, capture_output=True, text=True)

    def op_stub(self, body):
        path = self.root / "op"
        path.write_text(f"#!{sys.executable}\nimport sys\n" + body)
        path.chmod(0o755)

    def test_literal_and_argv_forwarding(self):
        result = self.run_cli("services", "get", "example-app/example-service", "-o", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "services get example-app/example-service -o json")
        self.assertNotIn("replace-with-your-key", result.stdout + result.stderr)

    def test_current_directory_env(self):
        self.assertEqual(self.run_cli("version", explicit=False).returncode, 0)

    def test_1password_resolves_reference(self):
        self.file.write_text("KOYEB_API_KEY=op://your-vault/your-item/your-field\n")
        self.op_stub("assert sys.argv[1:]==['read','op://your-vault/your-item/your-field']\nprint('replace-with-your-key')\n")
        self.assertEqual(self.run_cli("apps", "list").returncode, 0)

    def test_1password_failure_does_not_leak(self):
        self.file.write_text("KOYEB_API_KEY=op://your-vault/your-item/your-field\n")
        self.op_stub("print('sensitive-example-output')\nprint('sensitive-example-error',file=sys.stderr)\nsys.exit(7)\n")
        result = self.run_cli("apps", "list")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("sensitive-example", result.stdout + result.stderr)
        self.assertIn("exit 7", result.stderr)

    def test_missing_empty_credential_does_not_use_ambient(self):
        for content in ["", "KOYEB_API_KEY=\n", 'KOYEB_API_KEY="   "\n']:
            with self.subTest(content=content):
                self.file.write_text(content)
                self.assertEqual(self.run_cli("apps", "list").returncode, 1)
        self.file.unlink()
        self.assertEqual(self.run_cli("apps", "list").returncode, 1)

    def test_child_exit_status(self):
        for code in [0, 1, 7, 127]:
            self.env["CHILD_EXIT"] = str(code)
            self.assertEqual(self.run_cli("version").returncode, code)

    def test_rejected_flags_without_echoing_value(self):
        for flag in ["--token=private-example", "--token", "--debug-full", "--debug-full=true", "--url=https://example.com"]:
            result = self.run_cli("apps", "list", flag)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("private-example", result.stderr)
            self.assertEqual(result.stdout, "")

    def test_missing_binary(self):
        self.binary.unlink()
        self.assertEqual(self.run_cli("version").returncode, 127)

    def test_parser_quotes_comments_and_literal_shell_text(self):
        self.file.write_text("# comment\nexport KOYEB_API_KEY='$(do-not-run)#literal' # note\nOTHER=literal#suffix\n")
        values = module.read_env(self.file)
        self.assertEqual(values["KOYEB_API_KEY"], "$(do-not-run)#literal")
        self.assertEqual(values["OTHER"], "literal#suffix")
        self.env["EXPECTED_TOKEN"] = values["KOYEB_API_KEY"]
        self.assertEqual(self.run_cli("version").returncode, 0)

    def test_parser_rejects_malformed_without_value(self):
        for line in ['KOYEB_API_KEY="private-example', "not an assignment", "KOYEB_API_KEY=x\nKOYEB_API_KEY=y"]:
            self.file.write_text(line)
            result = self.run_cli("version")
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("private-example", result.stderr)

    def test_op_empty_and_multiline_output(self):
        self.file.write_text("KOYEB_API_KEY=op://your-vault/your-item/your-field\n")
        for body in ["print('')\n", "print('example-one\\nexample-two')\n"]:
            self.op_stub(body)
            self.assertEqual(self.run_cli("version").returncode, 1)

    def test_separator_and_help(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        result = subprocess.run([sys.executable, str(SCRIPT), "apps", "list"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
