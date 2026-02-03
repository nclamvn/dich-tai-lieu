"""
Test Suite: Vision Provider Fallback
AI Publisher Pro

Tests for Claude Vision → OpenAI Vision fallback mechanism.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_providers.unified_client import (
    UnifiedLLMClient,
    ProviderStatus,
    ProviderHealth,
    AllProvidersUnavailableError,
)


class TestVisionProviderOrder:
    """Test vision provider priority order."""

    def test_vision_provider_order_claude_first(self):
        """Vision requests should prioritize Claude over OpenAI."""
        client = UnifiedLLMClient()
        assert client.VISION_PROVIDER_ORDER == ["anthropic", "openai"]
        assert client.VISION_PROVIDER_ORDER[0] == "anthropic"

    def test_text_provider_order_openai_first(self):
        """Text requests should use standard order (OpenAI first)."""
        client = UnifiedLLMClient()
        assert client.PROVIDER_ORDER == ["openai", "anthropic", "deepseek"]
        assert client.PROVIDER_ORDER[0] == "openai"

    def test_deepseek_not_in_vision_order(self):
        """DeepSeek should not be in vision provider order (no vision support)."""
        client = UnifiedLLMClient()
        assert "deepseek" not in client.VISION_PROVIDER_ORDER

    def test_vision_model_config(self):
        """Verify vision model configuration for each provider."""
        client = UnifiedLLMClient()

        # Anthropic has vision
        assert client.PROVIDER_CONFIG["anthropic"]["vision_model"] is not None
        assert "claude" in client.PROVIDER_CONFIG["anthropic"]["vision_model"]

        # OpenAI has vision
        assert client.PROVIDER_CONFIG["openai"]["vision_model"] is not None
        assert "gpt-4o" == client.PROVIDER_CONFIG["openai"]["vision_model"]

        # DeepSeek has NO vision
        assert client.PROVIDER_CONFIG["deepseek"]["vision_model"] is None


class TestVisionContentDetection:
    """Test detection of vision content in messages."""

    def test_detect_anthropic_vision_format(self):
        """Detect Anthropic vision format (type: image)."""
        client = UnifiedLLMClient()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": "iVBORw0KGgo..."
                        }
                    }
                ]
            }
        ]
        assert client._has_vision_content(messages) is True

    def test_detect_openai_vision_format(self):
        """Detect OpenAI vision format (type: image_url)."""
        client = UnifiedLLMClient()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/png;base64,iVBORw0KGgo..."}
                    }
                ]
            }
        ]
        assert client._has_vision_content(messages) is True

    def test_text_only_no_vision(self):
        """Text-only messages should not be detected as vision."""
        client = UnifiedLLMClient()
        messages = [
            {"role": "user", "content": "Hello, translate this text"},
            {"role": "assistant", "content": "Sure, I'll help."},
        ]
        assert client._has_vision_content(messages) is False

    def test_text_list_no_vision(self):
        """Text content in list format without images."""
        client = UnifiedLLMClient()
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Just text here"}
                ]
            }
        ]
        assert client._has_vision_content(messages) is False


class TestVisionFormatConversion:
    """Test conversion between Anthropic and OpenAI vision formats."""

    def test_convert_anthropic_to_openai(self):
        """Convert Anthropic image format to OpenAI format."""
        client = UnifiedLLMClient()
        anthropic_content = [
            {"type": "text", "text": "Describe this"},
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": "abc123"
                }
            }
        ]

        openai_content = client._convert_vision_to_openai(anthropic_content)

        assert openai_content[0] == {"type": "text", "text": "Describe this"}
        assert openai_content[1]["type"] == "image_url"
        assert openai_content[1]["image_url"]["url"] == "data:image/jpeg;base64,abc123"

    def test_convert_openai_to_anthropic(self):
        """Convert OpenAI image format to Anthropic format."""
        client = UnifiedLLMClient()
        openai_content = [
            {"type": "text", "text": "What is this?"},
            {
                "type": "image_url",
                "image_url": {"url": "data:image/png;base64,xyz789"}
            }
        ]

        anthropic_content = client._convert_vision_to_anthropic(openai_content)

        assert anthropic_content[0] == {"type": "text", "text": "What is this?"}
        assert anthropic_content[1]["type"] == "image"
        assert anthropic_content[1]["source"]["type"] == "base64"
        assert anthropic_content[1]["source"]["media_type"] == "image/png"
        assert anthropic_content[1]["source"]["data"] == "xyz789"


class TestVisionFallbackLogic:
    """Test fallback behavior for vision requests."""

    @pytest.fixture
    def client_with_both_keys(self):
        """Client with both Anthropic and OpenAI keys configured."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "OPENAI_API_KEY": "test-openai-key",
        }):
            client = UnifiedLLMClient()
            yield client

    def test_vision_selects_anthropic_first(self, client_with_both_keys):
        """Vision request should select Anthropic first."""
        client = client_with_both_keys

        # Simulate vision content check
        messages_with_vision = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "..."}}
                ]
            }
        ]

        has_vision = client._has_vision_content(messages_with_vision)
        assert has_vision is True

        # Check provider order for vision
        for p in client.VISION_PROVIDER_ORDER:
            if p not in client._failed_providers:
                api_key = client._get_api_key(p)
                if api_key and client.PROVIDER_CONFIG[p].get("vision_model"):
                    first_vision_provider = p
                    break

        assert first_vision_provider == "anthropic"

    def test_fallback_to_openai_when_anthropic_fails(self, client_with_both_keys):
        """Should fallback to OpenAI when Anthropic fails."""
        client = client_with_both_keys

        # Mark Anthropic as failed
        client._failed_providers.add("anthropic")

        # Find next vision provider
        next_provider = None
        for p in client.VISION_PROVIDER_ORDER:
            if p not in client._failed_providers:
                if client.PROVIDER_CONFIG[p].get("vision_model"):
                    next_provider = p
                    break

        assert next_provider == "openai"

    def test_no_vision_fallback_to_deepseek(self, client_with_both_keys):
        """DeepSeek should never be selected for vision requests."""
        client = client_with_both_keys

        # Mark both vision providers as failed
        client._failed_providers.add("anthropic")
        client._failed_providers.add("openai")

        # Try to find vision provider
        next_provider = None
        for p in client.VISION_PROVIDER_ORDER:
            if p not in client._failed_providers:
                if client.PROVIDER_CONFIG[p].get("vision_model"):
                    next_provider = p
                    break

        # Should be None (no vision-capable provider available)
        assert next_provider is None
        # DeepSeek should NOT be selected
        assert "deepseek" not in client.VISION_PROVIDER_ORDER


class TestErrorClassification:
    """Test error classification for fallback decisions."""

    def test_classify_billing_error(self):
        """Billing errors should trigger fallback."""
        client = UnifiedLLMClient()

        billing_errors = [
            Exception("credit balance is too low"),
            Exception("insufficient_quota"),
            Exception("exceeded your current quota"),
            Exception("payment required"),
        ]

        for error in billing_errors:
            status = client._classify_error(error)
            assert status == ProviderStatus.NO_CREDIT

    def test_classify_invalid_key_error(self):
        """Invalid key errors should trigger fallback."""
        client = UnifiedLLMClient()

        key_errors = [
            Exception("invalid api key"),
            Exception("Unauthorized"),
            Exception("authentication failed"),
        ]

        for error in key_errors:
            status = client._classify_error(error)
            assert status == ProviderStatus.INVALID_KEY

    def test_classify_rate_limit_error(self):
        """Rate limit errors should NOT trigger permanent fallback."""
        client = UnifiedLLMClient()

        rate_errors = [
            Exception("rate_limit_exceeded"),
            Exception("Too many requests"),
            Exception("429 error"),
        ]

        for error in rate_errors:
            status = client._classify_error(error)
            assert status == ProviderStatus.RATE_LIMITED

    def test_retryable_errors(self):
        """Check which errors should trigger provider switch."""
        client = UnifiedLLMClient()

        # Should retry with different provider
        assert client._is_retryable_error(ProviderStatus.NO_CREDIT) is True
        assert client._is_retryable_error(ProviderStatus.INVALID_KEY) is True
        assert client._is_retryable_error(ProviderStatus.ERROR) is True

        # Should NOT retry (temporary issue)
        assert client._is_retryable_error(ProviderStatus.RATE_LIMITED) is False


class TestStatusSummary:
    """Test provider status summary including vision info."""

    @pytest.mark.asyncio
    async def test_status_includes_vision_providers(self):
        """Status summary should include vision provider info."""
        with patch.dict(os.environ, {
            "ANTHROPIC_API_KEY": "test-key",
            "OPENAI_API_KEY": "test-key",
        }):
            client = UnifiedLLMClient()

            # Mock validate_all_providers
            with patch.object(client, 'validate_all_providers', new_callable=AsyncMock) as mock_validate:
                mock_validate.return_value = {
                    "anthropic": ProviderHealth("anthropic", ProviderStatus.AVAILABLE),
                    "openai": ProviderHealth("openai", ProviderStatus.AVAILABLE),
                    "deepseek": ProviderHealth("deepseek", ProviderStatus.NOT_CONFIGURED),
                }

                status = await client.get_status_summary()

                assert "vision_providers" in status
                assert status["vision_providers"]["priority_order"] == ["anthropic", "openai"]
                assert "anthropic" in status["vision_providers"]["available"]
                assert "openai" in status["vision_providers"]["available"]

    @pytest.mark.asyncio
    async def test_vision_warning_when_no_vision_providers(self):
        """Should warn when no vision providers are available."""
        with patch.dict(os.environ, {
            "DEEPSEEK_API_KEY": "test-key",
        }, clear=True):
            client = UnifiedLLMClient()

            with patch.object(client, 'validate_all_providers', new_callable=AsyncMock) as mock_validate:
                mock_validate.return_value = {
                    "anthropic": ProviderHealth("anthropic", ProviderStatus.NOT_CONFIGURED),
                    "openai": ProviderHealth("openai", ProviderStatus.NOT_CONFIGURED),
                    "deepseek": ProviderHealth("deepseek", ProviderStatus.AVAILABLE),
                }

                status = await client.get_status_summary()

                assert "vision_warning" in status
                assert "No Vision providers" in status["vision_warning"]


class TestIntegrationScenarios:
    """Integration test scenarios for STEM document translation."""

    def test_stem_document_scenario(self):
        """
        Scenario: Translating STEM document with formula images.

        Expected behavior:
        1. Detect vision content (formula images)
        2. Select Claude Vision first
        3. If Claude fails, fallback to OpenAI Vision
        4. Never use DeepSeek for vision
        """
        client = UnifiedLLMClient()

        # Simulate STEM document with formula image
        stem_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Extract and translate this formula:"},
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": "formula_image_base64_data"
                    }
                }
            ]
        }

        # 1. Should detect as vision content
        assert client._has_vision_content([stem_message]) is True

        # 2. Vision provider order should be Claude first
        assert client.VISION_PROVIDER_ORDER[0] == "anthropic"

        # 3. DeepSeek should not have vision capability
        assert client.PROVIDER_CONFIG["deepseek"]["vision_model"] is None

    def test_text_only_stem_scenario(self):
        """
        Scenario: STEM document with LaTeX formulas (text-based).

        Expected: Use text provider order, not vision.
        """
        client = UnifiedLLMClient()

        # LaTeX formula as text (not image)
        latex_message = {
            "role": "user",
            "content": "Translate: The formula $\\sum_{i=1}^n x_i$ represents..."
        }

        # Should NOT detect as vision content
        assert client._has_vision_content([latex_message]) is False


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
