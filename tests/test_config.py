import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mini_agent.config import Settings, load_dotenv


class ConfigTests(unittest.TestCase):
    def test_explicit_dotenv_overrides_stale_process_key(self):
        with tempfile.TemporaryDirectory() as folder:
            env_path = Path(folder) / ".env"
            env_path.write_text(
                "DEEPSEEK_API_KEY=sk-new-project-key\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"DEEPSEEK_API_KEY": "sk-old-process-key"},
                clear=False,
            ):
                settings = Settings.from_env(env_path)
                self.assertEqual(settings.api_key, "sk-new-project-key")

    def test_commented_key_is_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            env_path = Path(folder) / ".env"
            env_path.write_text(
                "# DEEPSEEK_API_KEY=sk-commented-key\n",
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {"DEEPSEEK_API_KEY": "sk-process-key"},
                clear=False,
            ):
                load_dotenv(env_path)
                self.assertEqual(os.environ["DEEPSEEK_API_KEY"], "sk-process-key")


if __name__ == "__main__":
    unittest.main()
