"""Scoped budget and cleanup checks; no model calls."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import evening_smoke


class DiagnosticTests(unittest.TestCase):
    def test_only_output_budgets_changed(self):
        original = json.loads((ROOT / "configs/qwen-library.json").read_text())
        adjusted = json.loads((ROOT / "configs/qwen-budget-diagnostic.json").read_text())
        for stage, budget in (("answer_train", 1024), ("answer_eval", 1024), ("reflect", 2048)):
            self.assertEqual(adjusted["stages"][stage]["max_tokens"], budget)
            adjusted["stages"][stage]["max_tokens"] = original["stages"][stage]["max_tokens"]
        self.assertEqual(original, adjusted)

    def test_cleanup_cannot_hide_unload_or_service_errors(self):
        self.assertTrue(evening_smoke.cleanup_ok({"server_stopped": True}))
        for record in ({}, {"server_stopped": False}, {"server_stopped": True, "unload_error": "failed"},
                       {"server_stopped": True, "server_stop_error": "still alive"}):
            self.assertFalse(evening_smoke.cleanup_ok(record))

    def test_powershell_stop_checks_processes_and_port_after_nonzero_taskkill(self):
        # Execute the actual Stop branch against mocked OS commands in an isolated temporary root.
        for remaining in ("none", "reused", "server", "runner", "port"):
            with self.subTest(remaining=remaining), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / "scripts").mkdir()
                (root / "output/ollama-service").mkdir(parents=True)
                shutil.copyfile(ROOT / "scripts/ollama_service.ps1", root / "scripts/ollama_service.ps1")
                (root / "output/ollama-service/service.json").write_text(json.dumps({
                    "pid": 991, "executable": "fixture-ollama", "process_started_utc": "2026-01-01T00:00:00Z"}))
                source = r'''
$global:killed = $false
$global:remaining = 'REMAINING'
$global:started = [datetime]'2026-01-01T00:00:00Z'
function Get-Command { [pscustomobject]@{Source='fixture-ollama'} }
function Get-Process {
    param($Id)
    if ($global:killed -and $global:remaining -eq 'reused' -and $Id -eq 991) {
        return [pscustomobject]@{Id=$Id;Path='unrelated-app';StartTime=$global:started.AddHours(1)}
    }
    if (-not $global:killed -or ($global:remaining -eq 'server' -and $Id -eq 991) -or
        ($global:remaining -eq 'runner' -and $Id -eq 992)) {
        [pscustomobject]@{Id=$Id;Path='fixture-ollama';StartTime=$global:started}
    }
}
function Get-CimInstance {
    [pscustomobject]@{ProcessId=991;ParentProcessId=0;CreationDate=$global:started}
    [pscustomobject]@{ProcessId=992;ParentProcessId=991;CreationDate=$global:started}
}
function Get-NetTCPConnection { if ($global:remaining -eq 'port') { [pscustomobject]@{LocalPort=11436} } }
function Start-Sleep {}
function taskkill.exe { $global:killed=$true; $global:LASTEXITCODE=1 }
& (Join-Path $PSScriptRoot 'scripts/ollama_service.ps1') Stop -ExpectedProcessId 991
'''.replace("REMAINING", remaining)
                wrapper = root / "check.ps1"
                wrapper.write_text(source, encoding="utf-8")
                result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(wrapper)],
                                        capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode == 0, remaining in ("none", "reused"), result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
