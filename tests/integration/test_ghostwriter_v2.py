
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient

from core_v2.agents.ghostwriter.ghostwriter_agent import GhostwriterAgent
from core_v2.agents.ghostwriter.models import Variation
from api.main import app

# ============================================================================
# Unit Tests (Direct Agent Interaction)
# ============================================================================

@pytest.mark.unit
class TestGhostwriterAgentUnit:
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client for independent agent testing."""
        client = Mock()
        # Mock chat completion response structure if needed, 
        # but GhostwriterAgent._call_llm handles extraction.
        # We'll stick to mocking the output of _call_llm if possible,
        # or mock the client deeply.
        
        # Actually, simpler to mock the agent's _call_llm method directly 
        # for higher-level logic tests.
        return client

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Verify new V2 agent initializes correctly."""
        agent = GhostwriterAgent(agent_id="test_gw", llm_provider=None)
        assert agent.agent_id == "test_gw"
        assert agent.role == "ghostwriter"
        assert agent.get_status()["status"] == "ready"
        
        # Verify initial config load
        assert agent.config is not None
        assert "neutral" in agent.config.style_instructions

    @pytest.mark.asyncio
    async def test_propose_process_flow(self):
        """Test the 'process' method routing for 'propose' action."""
        agent = GhostwriterAgent(agent_id="test_gw", llm_provider=None)
        
        # Mock the internal logic to avoid LLM dependency here
        # (We want to test dispatching and arg parsing)
        agent.propose_next_paragraph = AsyncMock(return_value=[
            Variation(text="Var 1", style="neutral"),
            Variation(text="Var 2", style="creative")
        ])
        
        input_data = {
            "action": "propose",
            "params": {
                "context": "Once upon a time",
                "instruction": "Continue",
                "n_variations": 2
            }
        }
        
        result = await agent.process(input_data)
        
        # Verify dispatch
        agent.propose_next_paragraph.assert_called_once_with(
            context="Once upon a time",
            instruction="Continue",
            n_variations=2
        )
        
        # Verify output structure
        assert "variations" in result
        assert len(result["variations"]) == 2
        assert result["variations"][0]["text"] == "Var 1"


# ============================================================================
# Integration Tests (API + Agent)
# ============================================================================

@pytest.mark.integration
class TestGhostwriterAPIIntegration:
    
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_styles_endpoint(self, client):
        """Test GET /api/author/styles."""
        response = client.get("/api/author/styles")
        assert response.status_code == 200
        data = response.json()
        assert "styles" in data
        assert "neutral" in data["styles"]
        
    def test_propose_endpoint_mock(self, client):
        """Test POST /api/author/propose with mock engine."""
        
        # Patch the settings to force placeholder provider
        with patch("config.settings.settings.provider", "placeholder"):
            # Reset global engine to force re-initialization
            from api import routes
            routes.author._engine = None
            
            payload = {
                "context": "The night was dark.",
                "instruction": "Add suspense",
                "style": "neutral",
                "n_variations": 1
            }
            
            response = client.post("/api/author/propose", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check standard response structure
        assert "variations" in data
        assert "style" in data
        
        # In mock mode, it returns a placeholder
        # assert "[LLM Response Placeholder" in data["variations"][0]["text"]
        # New LLMClient placeholder returns JSON-like structure
        assert "Placeholder mode" in data["variations"][0]["text"]

    def test_rewrite_endpoint_mock(self, client):
        """Test POST /api/author/rewrite."""
        with patch("config.settings.settings.provider", "placeholder"):
            # Reset global engine
            from api import routes
            routes.author._engine = None

            payload = {
                "text": "Bad grammar here.",
                "improvements": ["Fix grammar"],
                "style": "neutral"
            }
            
            response = client.post("/api/author/rewrite", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert "rewritten_text" in data
        assert "original_text" in data

    def test_propose_stream_mock(self, client):
        """Test POST /api/author/propose/stream."""
        with patch("config.settings.settings.provider", "placeholder"):
            # Reset global engine
            from api import routes
            routes.author._engine = None

            payload = {
                "context": "Stream test",
                "instruction": "Go",
                "style": "neutral"
            }
            
            # Use client.stream() for streaming requests
            with client.stream("POST", "/api/author/propose/stream", json=payload) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers["content-type"]
                
                # Consume stream
                content = ""
                for line in response.iter_lines():
                    if line:
                        content += line + "\n"
                
                assert "data: {" in content
                assert "data: [DONE]" in content

