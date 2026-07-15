import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import app
from database import Base, get_db
from unittest.mock import patch, MagicMock

# 1. Setup an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_chat.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Dependency override
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after test
    Base.metadata.drop_all(bind=engine)

def test_1_1_disconnect_llm_error():
    """ID 1.1: Disconnect to internet or invalidate API KEY"""
    print("\nID: 1.1")
    print("Test: Disconnect to internet or invalidate API KEY")
    print("Expected: [Error communicating with LLM: Connection error. Please check if your GROQ_API_KEY is correct.]")
    
    # Mock the LLM instance itself
    with patch("main.llm") as mock_llm:
        mock_llm.bind_tools.return_value.astream.side_effect = Exception("Connection error")
        mock_llm.astream.side_effect = Exception("Connection error")
        
        response = client.post("/api/chat", json={"message": "Hello", "session_id": "test_session"})
        assert response.status_code == 200
        
        full_response = "".join([chunk.decode() for chunk in response.iter_bytes()])
        
        assert "Error communicating with LLM" in full_response
        assert "Connection error" in full_response
        print("Actual: As Expected")

def test_1_2_fetch_sessions():
    """ID 1.2: Send GET `/api/sessions` for fetching each sessions"""
    print("\nID: 1.2")
    print("Test: Send GET `/api/sessions` for fetching each sessions")
    print("Expected: \"GET /api/sessions HTTP/1.1\" 200 OK")
    
    response = client.get("/api/sessions")
    assert response.status_code == 200
    print("Actual: As Expected")

def test_1_3_fetch_history():
    """ID 1.3: Send GET `/api/history` for fetching chat history"""
    print("\nID: 1.3")
    print("Test: Send GET `/api/history` for fetching chat history")
    print("Expected: \"GET /api/history?session_id={session_id} HTTP/1.1\" 200 OK")
    
    session_id = "test_session"
    response = client.get(f"/api/history?session_id={session_id}")
    assert response.status_code == 200
    print("Actual: As Expected")

def test_1_4_send_chat_message():
    """ID 1.4: Send POST '/api/chat' for sending message to model and respond in streams"""
    print("\nID: 1.4")
    print("Test: Send POST '/api/chat' for sending message to model and respond in streams")
    print("Expected: \"POST /api/chat HTTP/1.1\" 200 OK")
    
    # Mock successful LLM stream
    with patch("main.llm") as mock_llm:
        mock_llm_with_tools = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm_with_tools
        
        async def mock_astream_generator(*args, **kwargs):
            mock_chunk = MagicMock()
            mock_chunk.tool_call_chunks = []
            mock_chunk.content = "Hello there!"
            yield mock_chunk

        mock_llm_with_tools.astream.side_effect = mock_astream_generator
        
        response = client.post("/api/chat", json={"message": "Hi", "session_id": "test_session"})
        assert response.status_code == 200
        print("Actual: As Expected")

def test_1_5_delete_session():
    """ID 1.5: Send DELETE '/api/sessions/{session_id}' for delete chat sessions"""
    print("\nID: 1.5")
    print("Test: Send DELETE '/api/sessions/{session_id}' for delete chat sessions")
    print("Expected: \"DELETE /api/sessions/{session_id} HTTP/1.1\" 200 OK")
    
    session_id = "test_session"
    response = client.delete(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    print("Actual: As Expected")

if __name__ == "__main__":
    import pytest
    # This allows the script to be run directly using 'python test_main.py'
    pytest.main([__file__, "-v", "-s"])
