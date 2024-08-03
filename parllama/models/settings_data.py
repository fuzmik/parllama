"""Model for application settings."""

from __future__ import annotations

import functools
import os
import shutil
from argparse import Namespace

import ollama
import simplejson as json
from pydantic import BaseModel

from parllama.utils import get_args
from parllama.utils import ScreenType
from parllama.utils import valid_screens


class Settings(BaseModel):
    """Model for application settings."""

    no_save: bool = False
    no_save_chat: bool = False
    data_dir: str = os.path.expanduser("~/.parllama")
    cache_dir: str = ""
    chat_dir: str = ""
    prompt_dir: str = ""
    export_md_dir: str = ""

    chat_tab_max_length: int = 15
    settings_file: str = "settings.json"
    theme_name: str = "par"
    starting_screen: ScreenType = "Local"
    last_screen: ScreenType = "Local"
    last_chat_model: str = ""
    last_chat_temperature: float | None = None
    last_chat_session_id: str | None = None
    theme_mode: str = "dark"
    site_models_namespace: str = ""
    max_log_lines: int = 1000
    ollama_host: str = "http://localhost:11434"
    ollama_ps_poll_interval: int = 3
    auto_name_session: bool = False
    auto_name_session_llm: str = ""

    # pylint: disable=too-many-branches, too-many-statements
    def __init__(self) -> None:
        """Initialize BwItemData."""
        super().__init__()
        args: Namespace = get_args()

        if args.no_save:
            self.no_save = True

        if args.no_chat_save:
            self.no_chat_save = True

        self.data_dir = (
            args.data_dir
            or os.environ.get("PARLLAMA_DATA_DIR")
            or os.path.expanduser("~/.parllama")
        )
        self.cache_dir = os.path.join(self.data_dir, "cache")
        self.chat_dir = os.path.join(self.data_dir, "chats")
        self.prompt_dir = os.path.join(self.data_dir, "prompts")
        self.export_md_dir = os.path.join(self.data_dir, "md_exports")

        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.chat_dir, exist_ok=True)
        os.makedirs(self.prompt_dir, exist_ok=True)
        os.makedirs(self.export_md_dir, exist_ok=True)

        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(
                f"Par Llama data directory does not exist: {self.data_dir}"
            )

        self.settings_file = os.path.join(self.data_dir, "settings.json")
        if args.restore_defaults:
            if os.path.exists(self.settings_file):
                os.unlink(self.settings_file)
            theme_file = os.path.join(self.data_dir, "themes", "par.json")
            if os.path.exists(theme_file):
                os.unlink(theme_file)
        if args.clear_cache:
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir, ignore_errors=True)
                os.makedirs(self.cache_dir, exist_ok=True)

        if args.purge_chats:
            if os.path.exists(self.chat_dir):
                shutil.rmtree(self.chat_dir, ignore_errors=True)
                os.makedirs(self.chat_dir, exist_ok=True)

        if args.purge_prompts:
            if os.path.exists(self.prompt_dir):
                shutil.rmtree(self.prompt_dir, ignore_errors=True)
                os.makedirs(self.prompt_dir, exist_ok=True)

        self.load_from_file()

        auto_name_session = os.environ.get("PARLLAMA_AUTO_NAME_SESSION")
        if args.auto_name_session is not None:
            self.auto_name_session = args.auto_name_session == "1"
        elif auto_name_session is not None:
            self.auto_name_session = auto_name_session == "1"

        url = os.environ.get("OLLAMA_URL")
        if args.ollama_url:
            url = args.ollama_url
        if url:
            if not (url.startswith("http://") or url.startswith("https://")):
                raise ValueError("Ollama URL must start with http:// or https://")
            self.ollama_host = url

        if os.environ.get("PARLLAMA_THEME_NAME"):
            self.theme_name = os.environ.get("PARLLAMA_THEME_NAME", self.theme_name)

        if os.environ.get("PARLLAMA_THEME_MODE"):
            self.theme_mode = os.environ.get("PARLLAMA_THEME_MODE", self.theme_mode)

        if args.theme_name:
            self.theme_name = args.theme_name
        if args.theme_mode:
            self.theme_mode = args.theme_mode

        if args.starting_screen:
            self.starting_screen = args.starting_screen.capitalize()
            if self.starting_screen not in valid_screens:
                self.starting_screen = "Local"

        if args.ps_poll:
            self.ollama_ps_poll_interval = args.ps_poll
        self.save_settings_to_file()

    def load_from_file(self) -> None:
        """Load settings from file."""
        try:
            with open(self.settings_file, encoding="utf-8") as f:
                data = json.load(f)
                url = data.get("ollama_host", self.ollama_host)

                if url.startswith("http://") or url.startswith("https://"):
                    self.ollama_host = url
                else:
                    print("ollama_host must start with http:// or https://")
                self.theme_name = data.get("theme_name", self.theme_name)
                self.theme_mode = data.get("theme_mode", self.theme_mode)
                self.site_models_namespace = data.get("site_models_namespace", "")
                self.starting_screen = data.get("starting_screen", "Local")
                if self.starting_screen not in valid_screens:
                    self.starting_screen = "Local"

                self.last_screen = data.get("last_screen", "Local")
                if self.last_screen not in valid_screens:
                    self.last_screen = self.starting_screen
                self.last_chat_model = data.get("last_chat_model", self.last_chat_model)
                self.last_chat_temperature = data.get("last_chat_temperature")
                self.last_chat_session_id = data.get(
                    "last_chat_session_id", self.last_chat_session_id
                )
                self.max_log_lines = max(0, data.get("max_log_lines", 1000))
                self.ollama_ps_poll_interval = data.get(
                    "ollama_ps_poll_interval", self.ollama_ps_poll_interval
                )
                self.auto_name_session = data.get(
                    "auto_name_session", self.auto_name_session
                )
                self.auto_name_session_llm = data.get(
                    "auto_name_session_llm", self.auto_name_session_llm
                )
                self.chat_tab_max_length = max(
                    8, data.get("chat_tab_max_length", self.chat_tab_max_length)
                )
        except FileNotFoundError:
            pass  # If file does not exist, continue with default settings

    def save_settings_to_file(self) -> None:
        """Save settings to file."""
        if self.no_save:
            return
        os.makedirs(self.data_dir, exist_ok=True)
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError(
                f"Par Llama data directory does not exist: {self.data_dir}"
            )

        with open(self.settings_file, "w", encoding="utf-8") as f:
            f.write(self.model_dump_json(indent=4))

    def ensure_cache_folder(self) -> None:
        """Ensure the cache folder exists."""
        if not os.path.exists(self.cache_dir):
            os.mkdir(self.cache_dir)

    @functools.cached_property
    def ollama_client(self) -> ollama.Client:
        """Get the ollama client."""
        return ollama.Client(host=self.ollama_host)


settings = Settings()
