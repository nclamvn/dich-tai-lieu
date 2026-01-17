import requests
import json
import sys

def test_api():
    base_url = "http://localhost:8000/api/author" # Assuming default port
    # Actually, the user runs uvicorn on port 3001 in README, but 8000 in main.py comments.
    # checking main.py... it says 8000 default.
    # Wait, in the README it said 3001.
    # Let's try to just import the app and test via TestClient to avoid port issues.
    
    from fastapi.testclient import TestClient
    from api.main import app
    
    client = TestClient(app)
    
    print("Testing /api/author/styles...")
    response = client.get("/api/author/styles")
    if response.status_code == 200:
        print("Styles endpoint: OK")
        print(response.json().keys())
    else:
        print(f"Styles endpoint FAILED: {response.status_code}")
        print(response.text)
        
    print("\nTesting /api/author/propose (mock)...")
    # Since LLM is None, it should return placeholder
    response = client.post("/api/author/propose", json={
        "context": "Hello world",
        "instruction": "Continue",
        "style": "neutral",
        "n_variations": 1
    })
    
    if response.status_code == 200:
        print("Propose endpoint: OK")
        print(response.json())
    else:
        print(f"Propose endpoint FAILED: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    test_api()
