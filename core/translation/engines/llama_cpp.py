"""
LlamaCpp Translation Engine — Uses llama.cpp server with GGUF models.

Provides stable, optimized inference on Apple Silicon by using llama.cpp's
Metal backend instead of PyTorch MPS.
"""

import asyncio
import logging
import subprocess
import os
from typing import Optional, List

import httpx

from .base import TranslationEngine, TranslationResult, EngineStatus

logger = logging.getLogger(__name__)


class LlamaCppEngine(TranslationEngine):
    """
    Translation engine using llama.cpp server with TranslateGemma GGUF.

    Architecture:
    1. Starts llama-server as subprocess (if not running)
    2. Sends translation requests via OpenAI-compatible API
    3. Returns translated text

    Benefits over PyTorch MPS:
    - Stable inference on Apple Silicon (Metal)
    - Lower memory usage with quantized models
    - Faster startup and generation
    """

    MODELS = {
        "translategemma-4b-q8": {
            "file": "translategemma-4b-it.Q8_0.gguf",
            "repo": "mradermacher/translategemma-4b-it-GGUF",
            "size_gb": 4.1,
            "quality": "high",
        },
        "translategemma-4b-q4": {
            "file": "translategemma-4b-it.Q4_K_M.gguf",
            "repo": "mradermacher/translategemma-4b-it-GGUF",
            "size_gb": 2.5,
            "quality": "good",
        },
        "translategemma-12b-q4": {
            "file": "translategemma-12b-it.Q4_K_M.gguf",
            "repo": "mradermacher/translategemma-12b-it-GGUF",
            "size_gb": 7.3,
            "quality": "best",
        },
    }

    SUPPORTED_LANGUAGES = [
        "ar", "bg", "bn", "ca", "cs", "da", "de", "el", "en", "es",
        "et", "fa", "fi", "fr", "gu", "he", "hi", "hr", "hu", "id",
        "it", "ja", "kn", "ko", "lt", "lv", "ml", "mr", "ms", "nl",
        "no", "pa", "pl", "pt", "ro", "ru", "sk", "sl", "sr", "sv",
        "sw", "ta", "te", "th", "tl", "tr", "uk", "ur", "vi", "zh", "zu",
    ]

    LANG_NAMES = {
        "en": "English", "vi": "Vietnamese", "zh": "Chinese",
        "ja": "Japanese", "ko": "Korean", "fr": "French",
        "de": "German", "es": "Spanish", "pt": "Portuguese",
        "ru": "Russian", "ar": "Arabic", "th": "Thai",
        "id": "Indonesian", "ms": "Malay", "tl": "Filipino",
        "it": "Italian", "nl": "Dutch", "pl": "Polish",
        "tr": "Turkish", "sv": "Swedish", "da": "Danish",
        "fi": "Finnish", "no": "Norwegian", "cs": "Czech",
        "ro": "Romanian", "hu": "Hungarian", "el": "Greek",
        "he": "Hebrew", "hi": "Hindi", "bn": "Bengali",
        "ta": "Tamil", "te": "Telugu", "ur": "Urdu",
        "fa": "Persian", "uk": "Ukrainian", "bg": "Bulgarian",
        "hr": "Croatian", "sk": "Slovak", "sl": "Slovenian",
        "sr": "Serbian", "et": "Estonian", "lv": "Latvian",
        "lt": "Lithuanian", "ca": "Catalan", "sw": "Swahili",
        "gu": "Gujarati", "kn": "Kannada", "ml": "Malayalam",
        "mr": "Marathi", "pa": "Punjabi", "zu": "Zulu",
    }

    def __init__(
        self,
        model_id: str = "translategemma-4b-q8",
        models_dir: Optional[str] = None,
        server_host: str = "127.0.0.1",
        server_port: int = 8080,
        context_size: int = 2048,
        n_gpu_layers: int = -1,
    ):
        self.model_id = model_id
        self.models_dir = models_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "models",
        )
        self.server_host = server_host
        self.server_port = server_port
        self.context_size = context_size
        self.n_gpu_layers = n_gpu_layers

        self._server_process: Optional[subprocess.Popen] = None
        self._status = EngineStatus.UNAVAILABLE
        self._error: Optional[str] = None

        self._model_path = self._get_model_path()

    @property
    def name(self) -> str:
        model_info = self.MODELS.get(self.model_id, {})
        quality = model_info.get("quality", "unknown")
        return f"TranslateGemma GGUF ({quality})"

    @property
    def engine_id(self) -> str:
        return f"llama_cpp_{self.model_id}"

    @property
    def supported_languages(self) -> List[str]:
        return self.SUPPORTED_LANGUAGES

    def _get_model_path(self) -> Optional[str]:
        model_info = self.MODELS.get(self.model_id)
        if not model_info:
            return None
        model_path = os.path.join(self.models_dir, model_info["file"])
        return model_path if os.path.exists(model_path) else None

    def is_available(self) -> bool:
        try:
            result = subprocess.run(
                ["which", "llama-server"],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                self._error = "llama-server not installed. Run: brew install llama.cpp"
                return False
        except Exception as e:
            self._error = f"Cannot check llama-server: {e}"
            return False

        if not self._model_path:
            model_info = self.MODELS.get(self.model_id, {})
            self._error = (
                f"Model not found. Download: huggingface-cli download "
                f"{model_info.get('repo', '?')} {model_info.get('file', '?')} "
                f"--local-dir {self.models_dir}"
            )
            return False

        return True

    async def _ensure_server_running(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"http://{self.server_host}:{self.server_port}/health",
                    timeout=2.0,
                )
                if resp.status_code == 200:
                    self._status = EngineStatus.AVAILABLE
                    return True
        except Exception:
            pass

        if not self._model_path:
            self._error = "Model not found"
            return False

        logger.info("Starting server with %s...", self.model_id)
        self._status = EngineStatus.LOADING

        try:
            cmd = [
                "llama-server",
                "-m", self._model_path,
                "--host", self.server_host,
                "--port", str(self.server_port),
                "-c", str(self.context_size),
                "-ngl", str(self.n_gpu_layers),
                "--log-disable",
            ]

            self._server_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )

            for i in range(60):
                await asyncio.sleep(1)
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(
                            f"http://{self.server_host}:{self.server_port}/health",
                            timeout=2.0,
                        )
                        if resp.status_code == 200:
                            logger.info("Server ready after %ds", i + 1)
                            self._status = EngineStatus.AVAILABLE
                            return True
                except Exception:
                    continue

            self._error = "Server startup timeout (60s)"
            self._status = EngineStatus.ERROR
            return False

        except Exception as e:
            self._error = f"Failed to start server: {e}"
            self._status = EngineStatus.ERROR
            return False

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        **kwargs,
    ) -> TranslationResult:
        if not await self._ensure_server_running():
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=self.engine_id,
                success=False,
                error=self._error or "Server not available",
            )

        src_name = self.LANG_NAMES.get(source_lang, source_lang.upper())
        tgt_name = self.LANG_NAMES.get(target_lang, target_lang.upper())
        prompt = f"Translate from {src_name} to {tgt_name}:\n\n{text}"

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"http://{self.server_host}:{self.server_port}/v1/chat/completions",
                    json={
                        "model": self.model_id,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": min(len(text) * 3, 2048),
                        "temperature": 0.0,
                        "stream": False,
                    },
                    timeout=120.0,
                )

                if resp.status_code != 200:
                    return TranslationResult(
                        translated_text="",
                        source_lang=source_lang,
                        target_lang=target_lang,
                        engine=self.engine_id,
                        success=False,
                        error=f"Server error: {resp.status_code}",
                    )

                data = resp.json()
                translated = data["choices"][0]["message"]["content"].strip()
                usage = data.get("usage", {})

                return TranslationResult(
                    translated_text=translated,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    engine=self.engine_id,
                    success=True,
                    tokens_used=usage.get("total_tokens", 0),
                    cost=0.0,
                    metadata={
                        "model": self.model_id,
                        "prompt_tokens": usage.get("prompt_tokens", 0),
                        "completion_tokens": usage.get("completion_tokens", 0),
                    },
                )

        except httpx.TimeoutException:
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=self.engine_id,
                success=False,
                error="Translation timeout (120s)",
            )
        except Exception as e:
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=self.engine_id,
                success=False,
                error=str(e),
            )

    def stop_server(self):
        if self._server_process:
            self._server_process.terminate()
            self._server_process.wait()
            self._server_process = None
            self._status = EngineStatus.UNAVAILABLE
            logger.info("Server stopped")

    def get_info(self) -> dict:
        model_info = self.MODELS.get(self.model_id, {})
        info = super().get_info()
        info.update({
            "model": self.model_id,
            "model_file": model_info.get("file"),
            "size_gb": model_info.get("size_gb"),
            "quality": model_info.get("quality"),
            "offline": True,
            "cost_per_token": 0.0,
            "server_url": f"http://{self.server_host}:{self.server_port}",
            "error": self._error,
        })
        return info

    def get_status(self) -> EngineStatus:
        if self._status in (EngineStatus.LOADING, EngineStatus.ERROR):
            return self._status
        return super().get_status()

    def __del__(self):
        self.stop_server()
