import pytest
from app.agent import CensusAgent

def test_extract_structured_json_clean():
    agent = CensusAgent(session_id="test_session")
    raw_text = """
{
  "answer": "This is a test answer.",
  "citations": [
    {
      "source_document": "doc.pdf",
      "page_number": 1,
      "snippet": "test snippet"
    }
  ],
  "artifacts": [
    {
      "name": "test.png",
      "type": "image",
      "description": "test image"
    }
  ]
}
    """
    res = agent.extract_structured_json(raw_text)
    assert res["answer"] == "This is a test answer."
    assert len(res["citations"]) == 1
    assert res["citations"][0]["source_document"] == "doc.pdf"
    assert len(res["artifacts"]) == 1
    assert res["artifacts"][0]["name"] == "test.png"

def test_extract_structured_json_with_markdown_wrapper():
    agent = CensusAgent(session_id="test_session")
    raw_text = """
Here is the result:
```json
{
  "answer": "Answer wrapped in markdown.",
  "citations": [],
  "artifacts": []
}
```
Thank you!
    """
    res = agent.extract_structured_json(raw_text)
    assert res["answer"] == "Answer wrapped in markdown."
    assert len(res["citations"]) == 0
    assert len(res["artifacts"]) == 0

def test_extract_structured_json_invalid_fallback():
    agent = CensusAgent(session_id="test_session")
    raw_text = "This is not JSON text at all."
    res = agent.extract_structured_json(raw_text)
    assert res["answer"] == "This is not JSON text at all."
    assert len(res["citations"]) == 0
    assert len(res["artifacts"]) == 0

def test_reasoning_effort_initialization():
    agent = CensusAgent(session_id="test_session", model="gpt-oss-120b", reasoning_effort="high")
    assert agent.model == "gpt-oss-120b"
    assert agent.reasoning_effort == "high"

    agent_default = CensusAgent(session_id="test_session")
    assert agent_default.reasoning_effort == "medium"

