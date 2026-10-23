"""Check the launch contract without downloading multi-gigabyte model weights."""

import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "packages/infinity-setup/root/usr/bin/infinity-local-ai"
LOADER = importlib.machinery.SourceFileLoader("infinity_local_ai", str(SOURCE))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
wrapper = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(wrapper)


class LocalAiWrapperTests(unittest.TestCase):
    def test_check_loads_the_selected_model_in_opencode(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/infinityos/local-ai-model"
            config.parent.mkdir(parents=True)
            config.write_text("infinity-qwen-9b\n")
            binary = home / ".local/bin/opencode"
            binary.parent.mkdir(parents=True)
            binary.touch()

            def run(command, **kwargs):
                if command[1] == "show":
                    return SimpleNamespace(returncode=0)
                settings = json.loads(kwargs["env"]["OPENCODE_CONFIG_CONTENT"])
                self.assertEqual(settings["model"], "ollama/infinity-qwen-9b")
                self.assertEqual(settings["permission"]["edit"], "ask")
                self.assertEqual(settings["permission"]["external_directory"], "ask")
                return SimpleNamespace(returncode=0, stdout="ollama/infinity-qwen-9b\n")

            with patch.object(wrapper.Path, "home", return_value=home), \
                 patch.object(wrapper.shutil, "which", side_effect=lambda name: "/usr/bin/ollama" if name == "ollama" else None), \
                 patch.object(wrapper.subprocess, "run", side_effect=run), \
                 patch.object(wrapper.sys, "argv", ["infinity-local-ai", "--check"]):
                wrapper.main()

    def test_edit_tab_allows_disk_edits_but_asks_before_shell(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".config/infinityos/local-ai-model"
            config.parent.mkdir(parents=True)
            config.write_text("infinity-gemma-12b\n")
            binary = home / ".local/bin/opencode"
            binary.parent.mkdir(parents=True)
            binary.touch()
            with patch.object(wrapper.Path, "home", return_value=home), \
                 patch.object(wrapper.shutil, "which", side_effect=lambda name: "/usr/bin/ollama" if name == "ollama" else None), \
                 patch.object(wrapper.subprocess, "run", return_value=SimpleNamespace(returncode=0)), \
                 patch.object(wrapper.os, "execve") as execute, \
                 patch.object(wrapper.sys, "argv", ["infinity-local-ai", "--edit"]):
                wrapper.main()
            settings = json.loads(execute.call_args.args[2]["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(settings["permission"]["edit"], "allow")
            self.assertEqual(settings["permission"]["external_directory"], "allow")
            self.assertEqual(settings["permission"]["bash"], "ask")
            self.assertEqual(execute.call_args.args[1][-1], "ollama/infinity-gemma-12b")


if __name__ == "__main__":
    unittest.main()
