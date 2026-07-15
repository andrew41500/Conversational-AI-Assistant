import asyncio
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
from dotenv import load_dotenv

from database import get_db, Message as DBMessage
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_core.tools import tool
import requests

load_dotenv()

@tool
def generate_chart(title: str, chart_type: str, x_data: list[str], y_data: list[float], x_label: str = "", y_label: str = "") -> str:
    """Generates a visualization chart for data using the external MCP server. 
    Use this tool whenever the user asks to see a chart, graph, or plot.
    """
    try:
        # Defaults to localhost for local dev, or mcp-server in docker
        mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8001")
        response = requests.post(f"{mcp_url}/generate_chart", json={
            "title": title,
            "chart_type": chart_type,
            "x_data": x_data,
            "y_data": y_data,
            "x_label": x_label,
            "y_label": y_label
        }, timeout=10)
        response.raise_for_status()
        data = response.json()
        base64_img = data.get("image_base64")
        if base64_img:
            return f"[CHART:data:image/png;base64,{base64_img}]"
        return "[Error: MCP Server returned no image]"
    except Exception as e:
        return f"[Error: Failed to call MCP Server: {str(e)}]"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NOTE: If you install Ollama locally in the future, you can swap to this:
# from langchain_community.chat_models import ChatOllama
# llm = ChatOllama(model="llama3", streaming=True)

llm = ChatGroq(
    model="llama-3.3-70b-versatile", 
    api_key=os.getenv("GROQ_API_KEY", "your_groq_api_key_here"), 
    temperature=0.7, 
    streaming=True
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"

@app.get("/api/history")
def get_history(session_id: str = "default_session", db: Session = Depends(get_db)):
    """Fetch chat history for the session"""
    messages = db.query(DBMessage).filter(DBMessage.session_id == session_id).order_by(DBMessage.timestamp.asc()).all()
    return {"messages": [{"role": m.role, "content": m.content} for m in messages]}

@app.get("/api/sessions")
def get_sessions(db: Session = Depends(get_db)):
    """Fetch all unique sessions and generate a title from the first user message"""
    # Get all user messages ordered by timestamp to find the first message of each session
    user_messages = db.query(DBMessage).filter(DBMessage.role == "user").order_by(DBMessage.timestamp.asc()).all()
    
    sessions_dict = {}
    for msg in user_messages:
        if msg.session_id not in sessions_dict:
            # Create a short title from the first message
            title = msg.content[:30] + ("..." if len(msg.content) > 30 else "")
            sessions_dict[msg.session_id] = title
            
    # Return list in reverse chronological order (newest first)
    sessions_list = [{"id": k, "title": v} for k, v in sessions_dict.items()]
    sessions_list.reverse()
    
    return {"sessions": sessions_list}
    
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str, db: Session = Depends(get_db)):
    """Delete all messages for a specific session"""
    db.query(DBMessage).filter(DBMessage.session_id == session_id).delete()
    db.commit()
    return {"status": "success", "message": f"Session {session_id} deleted"}

@app.post("/api/chat")
async def chat_stream(request: ChatRequest, db: Session = Depends(get_db)):
    user_msg_content = request.message
    session_id = request.session_id

    # 1. Save user msg to DB
    user_db_msg = DBMessage(session_id=session_id, role="user", content=user_msg_content)
    db.add(user_db_msg)
    db.commit()

    # 2. Fetch history from DB to pass to LLM
    db_history = db.query(DBMessage).filter(DBMessage.session_id == session_id).order_by(DBMessage.timestamp.asc()).all()
    
    import re
    lc_messages = [SystemMessage(content="You are a helpful AI assistant. You can generate charts using your tools. After generated the charts and sent to the user and user reply anything that is not requesting for generate the chart, please reply the user in text, and make sure you don't send the chart again only if the user request you to send the generated chart again or want you to generate a new chart for the user. If the user thanks you for a chart, simply say you're welcome.")]
    for msg in db_history:
        # Prevent the LLM from getting stuck repeating tool calls by rewriting the history
        # so it thinks it organically provided the chart already.
        # Dynamically extract the title and replace it in history so the LLM has better context
        def replace_with_title(m):
            content = m.group(0)
            title_match = re.search(r"generate '(.*?)'", content)
            title = title_match.group(1) if title_match else "the chart"
            return f'"{title}" generated'

        clean_content = re.sub(
            r'(\n\*Calling external MCP Data Server.*?\n)?\[CHART:data:image/png;base64,.*?\]', 
            replace_with_title, 
            msg.content,
            flags=re.DOTALL
        )
        
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=clean_content))
        else:
            lc_messages.append(AIMessage(content=clean_content))

    # 3. Stream Generator
    async def generate_response():
        full_response = ""
        try:
            llm_with_tools = llm.bind_tools([generate_chart])
            is_tool_call = False
            gathered = None
            
            # We use astream to asynchronously stream tokens or tool calls
            async for chunk in llm_with_tools.astream(lc_messages):
                if chunk.tool_call_chunks:
                    is_tool_call = True
                    gathered = chunk if gathered is None else gathered + chunk
                elif not is_tool_call:
                    content = chunk.content
                    if content:
                        full_response += content
                        yield content
                        await asyncio.sleep(0.04)
                        
            if is_tool_call and gathered and gathered.tool_calls:
                # We have a complete tool call parsing we can execute
                tool_call = gathered.tool_calls[0]
                args = tool_call["args"]
                
                yield f"\n*Calling external MCP Data Server to generate '{args.get('title', 'chart')}'...*\n"
                
                # Execute tool
                tool_result = generate_chart.invoke(args)
                full_response += tool_result
                yield tool_result

        except Exception as e:
            error_msg = str(e)
            # Check for token limit or rate limit errors specifically
            if "rate_limit_exceeded" in error_msg or "413" in error_msg or "TPM" in error_msg:
                yield f"\n\n[Your message is too long for the AI to process. Please try a shorter message or start a new chat.]"
            else:
                yield f"\n\n[Error communicating with LLM: {error_msg}\nPlease check if your GROQ_API_KEY is correct.]"
        finally:
            # Save AI Response to Database
            from database import SessionLocal
            db_bg = SessionLocal()
            try:
                ai_db_msg = DBMessage(session_id=session_id, role="ai", content=full_response)
                db_bg.add(ai_db_msg)
                db_bg.commit()
            finally:
                db_bg.close()

    return StreamingResponse(generate_response(), media_type="text/plain")
