import sys
import os
from pathlib import Path
import asyncio

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from core_v2.agents.ghostwriter.ghostwriter_agent import GhostwriterAgent

async def test_agent():
    print("Testing GhostwriterAgent import and instantiation...")
    
    agent = GhostwriterAgent(
        agent_id="test_ghostwriter_01",
        llm_provider=None 
    )
    
    print(f"Agent initialized: {agent.agent_id}")
    print(f"Role: {agent.role}")
    
    status = agent.get_status()
    print(f"Status: {status}")
    
    # Test process with placeholder LLM
    result = await agent.process({
        "action": "propose",
        "params": {
            "context": "Once upon a time",
            "instruction": "Continue the story"
        }
    })
    
    print(f"Process Result: {result}")
    
    assert "result" in result or "variations" in result
    print("Test PASSED!")

if __name__ == "__main__":
    asyncio.run(test_agent())
