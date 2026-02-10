"""
TranslateGemma Translation Engine
Google's open translation model optimized for Apple Silicon (MPS)
"""

import asyncio
import logging
from typing import List, Optional
from .base import TranslationEngine, TranslationResult, EngineStatus

logger = logging.getLogger(__name__)
from ..language_codes import TRANSLATEGEMMA_LANGUAGES


class TranslateGemmaEngine(TranslationEngine):
    """
    TranslateGemma-4B translation engine.
    Optimized for Apple Silicon M1/M2/M3 with MPS backend.

    Features:
    - 55 language support
    - Offline operation
    - Zero cost per translation
    - ~8GB memory usage (float16)
    """

    def __init__(
        self,
        model_size: str = "4b",
        device: Optional[str] = None,
        auto_load: bool = False
    ):
        """
        Initialize TranslateGemma engine.

        Args:
            model_size: Model size ("4b", "12b", "27b") - only 4b for 16GB RAM
            device: Force device ("mps", "cuda", "cpu") or None for auto-detect
            auto_load: Load model immediately if True
        """
        self.model_size = model_size
        self.model_id = f"google/translategemma-{model_size}-it"
        self._device = device or self._detect_device()
        self._model = None
        self._processor = None
        self._loaded = False
        self._loading = False
        self._error: Optional[str] = None

        if auto_load:
            asyncio.create_task(self._load_model_async())

    @property
    def name(self) -> str:
        return f"TranslateGemma {self.model_size.upper()}"

    @property
    def engine_id(self) -> str:
        return f"translategemma_{self.model_size}"

    @property
    def supported_languages(self) -> List[str]:
        return TRANSLATEGEMMA_LANGUAGES

    @property
    def device(self) -> str:
        return self._device

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    def _detect_device(self) -> str:
        """Detect best available device"""
        try:
            import torch
            if torch.backends.mps.is_available():
                return "mps"
            elif torch.cuda.is_available():
                return "cuda"
        except ImportError:
            pass
        return "cpu"

    def _check_memory(self) -> bool:
        """Check if enough memory available"""
        try:
            import subprocess

            if self._device == "mps":
                # NOTE: MPS has known issues with TranslateGemma generation
                # The model loads but generates only pad tokens
                # Until this is fixed, we recommend using Cloud API
                # See: https://github.com/huggingface/transformers/issues
                logger.warning("MPS support is experimental and may not work correctly")

                # Check macOS unified memory
                result = subprocess.run(
                    ["sysctl", "hw.memsize"],
                    capture_output=True,
                    text=True
                )
                total_gb = int(result.stdout.split()[-1]) / (1024**3)
                # 4B model needs ~8GB, leave 4GB for OS
                return total_gb >= 12

            elif self._device == "cuda":
                import torch
                vram_gb = torch.cuda.get_device_properties(0).total_memory / 1e9
                required = {"4b": 8, "12b": 24, "27b": 54}
                return vram_gb >= required.get(self.model_size, 8)

            return True  # CPU always "available" (but slow)

        except Exception:
            return False

    def is_available(self) -> bool:
        """Check if engine can be used"""
        if self._error:
            return False
        if self._loading:
            return False
        if not self._check_memory():
            return False

        # Check if transformers is installed
        try:
            import transformers
            import torch
            return True
        except ImportError:
            self._error = "transformers or torch not installed"
            return False

    def get_status(self) -> EngineStatus:
        """Get detailed engine status"""
        if self._error:
            return EngineStatus.ERROR
        if self._loading:
            return EngineStatus.LOADING
        if self._loaded:
            return EngineStatus.AVAILABLE
        if self.is_available():
            return EngineStatus.AVAILABLE
        return EngineStatus.UNAVAILABLE

    def load_model(self) -> bool:
        """
        Load model synchronously with HF token authentication.
        Call this before first translation or let translate() auto-load.

        Returns:
            True if model loaded successfully
        """
        if self._loaded:
            return True

        if self._loading:
            return False

        self._loading = True

        try:
            import os
            import torch
            from transformers import AutoModelForImageTextToText, AutoProcessor

            # Get HF token from environment
            hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGINGFACE_TOKEN')

            logger.info("Loading %s on %s...", self.model_id, self._device)
            if hf_token:
                logger.info("Using HF token for authentication")

            # Load processor with token
            self._processor = AutoProcessor.from_pretrained(
                self.model_id,
                token=hf_token,
                trust_remote_code=True
            )

            # Load model with device-specific settings
            model_kwargs = {
                "torch_dtype": torch.float16,
                "low_cpu_mem_usage": True,
            }

            # Add token to model kwargs
            if hf_token:
                model_kwargs["token"] = hf_token

            if self._device == "cuda":
                model_kwargs["device_map"] = "auto"

            self._model = AutoModelForImageTextToText.from_pretrained(
                self.model_id,
                **model_kwargs
            )

            # Move to MPS if needed
            if self._device == "mps":
                self._model = self._model.to("mps")

            self._loaded = True
            self._loading = False
            logger.info("Model loaded successfully on %s", self._device)
            return True

        except Exception as e:
            self._error = str(e)
            self._loading = False
            logger.warning("Failed to load model: %s", e)
            return False

    async def _load_model_async(self) -> bool:
        """Load model asynchronously"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.load_model)

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        **kwargs
    ) -> TranslationResult:
        """
        Translate text using TranslateGemma.

        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code

        Returns:
            TranslationResult with translated text
        """
        # Validate languages
        if not self.supports_language(source_lang):
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=self.engine_id,
                success=False,
                error=f"Source language '{source_lang}' not supported"
            )

        if not self.supports_language(target_lang):
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=self.engine_id,
                success=False,
                error=f"Target language '{target_lang}' not supported"
            )

        # Load model if not loaded
        if not self._loaded:
            success = await self._load_model_async()
            if not success:
                return TranslationResult(
                    translated_text="",
                    source_lang=source_lang,
                    target_lang=target_lang,
                    engine=self.engine_id,
                    success=False,
                    error=self._error or "Failed to load model"
                )

        try:
            import torch

            # Prepare message in TranslateGemma format
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "source_lang_code": source_lang,
                            "target_lang_code": target_lang,
                            "text": text,
                        }
                    ],
                }
            ]

            # Tokenize
            inputs = self._processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt"
            )

            # Move to device with correct dtype
            # MPS works best with float16, CUDA can use bfloat16
            target_dtype = torch.float16 if self._device == "mps" else torch.bfloat16

            if self._device in ["mps", "cuda"]:
                inputs = {k: v.to(self._model.device, dtype=target_dtype if v.dtype == torch.float32 else None)
                          for k, v in inputs.items()}

            input_len = len(inputs['input_ids'][0])

            # Generate translation (following official example)
            with torch.inference_mode():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=min(len(text) * 3, 2048),
                    do_sample=False,
                )

            # Decode output
            output_tokens = outputs[0][input_len:]
            translated = self._processor.decode(
                output_tokens,
                skip_special_tokens=True
            ).strip()

            tokens_used = len(output_tokens)

            return TranslationResult(
                translated_text=translated,
                source_lang=source_lang,
                target_lang=target_lang,
                engine=self.engine_id,
                success=True,
                tokens_used=tokens_used,
                cost=0.0,  # FREE!
                metadata={
                    "device": self._device,
                    "model": self.model_id
                }
            )

        except Exception as e:
            return TranslationResult(
                translated_text="",
                source_lang=source_lang,
                target_lang=target_lang,
                engine=self.engine_id,
                success=False,
                error=str(e)
            )

    def unload_model(self):
        """Unload model to free memory"""
        if self._model:
            del self._model
            self._model = None

        if self._processor:
            del self._processor
            self._processor = None

        self._loaded = False

        # Clear device cache
        try:
            import torch
            if self._device == "mps":
                torch.mps.empty_cache()
            elif self._device == "cuda":
                torch.cuda.empty_cache()
        except Exception:
            pass

        logger.info("Model unloaded, memory freed")

    def get_info(self) -> dict:
        """Get engine information"""
        info = super().get_info()
        info.update({
            "model_id": self.model_id,
            "model_size": self.model_size,
            "device": self._device,
            "loaded": self._loaded,
            "cost_per_token": 0.0,
            "offline": True,
        })
        if self._error:
            info["error"] = self._error
        # Warn about MPS compatibility
        if self._device == "mps":
            info["warning"] = "MPS support is experimental - generation may not work correctly"
        return info
