import streamlit as st
import requests
import uuid
import os
import re
import json

# Page config
st.set_page_config(
    page_title="Census Q&A Chatbot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend URL configuration
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# Custom Premium Styling (Perplexity-inspired)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"], .stMarkdown {
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background-color: #191a1a;
        color: #e3e3e3;
    }
    
    /* Center container maximum width */
    .block-container {
        max-width: 850px !important;
        padding-top: 3rem !important;
        padding-bottom: 8rem !important;
    }
    
    /* Sidebar layout */
    section[data-testid="stSidebar"] {
        background-color: #131414 !important;
        border-right: 1px solid #2d3030;
    }
    
    /* Input formatting override */
    div[data-testid="stTextInput"] {
        background-color: #202222 !important;
        border: 1px solid #2d3030 !important;
        border-radius: 12px !important;
        padding: 4px !important;
    }
    div[data-testid="stTextInput"] input {
        color: #e3e3e3 !important;
        background-color: transparent !important;
        border: none !important;
        font-size: 1.05rem !important;
    }
    
    /* Chat bubbles styling */
    .stChatMessage {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 1px solid #2d3030 !important;
        border-radius: 0px !important;
        padding: 24px 0px !important;
    }
    
    /* Expander styling */
    div[data-testid="stExpander"] {
        background-color: #1c1e1e !important;
        border: 1px solid #2d3030 !important;
        border-radius: 8px !important;
        margin-top: 10px;
    }
    
    /* Source box detail style */
    .citation-box {
        background-color: #202222;
        border-left: 3px solid #13c2c2;
        padding: 12px;
        border-radius: 4px;
        margin-top: 8px;
        font-size: 0.88rem;
        color: #c9c9c9;
    }
    
    /* Logs trace style */
    .log-box {
        background-color: #131414;
        font-family: monospace;
        padding: 10px;
        border-radius: 6px;
        border: 1px solid #2d3030;
        color: #8a8f98;
        max-height: 250px;
        overflow-y: auto;
        font-size: 0.85rem;
    }
    
    /* General Button override */
    div.stButton > button {
        background-color: #202222 !important;
        color: #e3e3e3 !important;
        border: 1px solid #2d3030 !important;
        border-radius: 20px !important;
        padding: 6px 16px !important;
        font-size: 0.88rem !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:hover {
        border-color: #13c2c2 !important;
        color: #13c2c2 !important;
        background-color: #1c1e1e !important;
    }
    
    /* Chat input panel styling at bottom */
    div[data-testid="stChatInput"] {
        background-color: #202222 !important;
        border: 1px solid #2d3030 !important;
        border-radius: 16px !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #e3e3e3 !important;
    }
    
    /* Citations superscript links */
    sup a {
        color: #13c2c2 !important;
        text-decoration: none;
        font-weight: bold;
    }
    sup a:hover {
        text-decoration: underline !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to format superscripts inside answers
def format_superscripts(text, citations):
    if not citations:
        return text
        
    seen = set()
    unique_cites = []
    for cite in citations:
        key = (cite["source_document"], cite["page_number"])
        if key not in seen:
            seen.add(key)
            unique_cites.append(cite)
            
    idx_map = {}
    for orig_idx, cite in enumerate(citations):
        key = (cite["source_document"], cite["page_number"])
        for u_idx, u_cite in enumerate(unique_cites):
            if (u_cite["source_document"], u_cite["page_number"]) == key:
                idx_map[orig_idx + 1] = u_idx + 1
                break
                
    def repl(match):
        num = int(match.group(1))
        if num in idx_map:
            mapped_num = idx_map[num]
            return f'<sup><a href="#cite-{mapped_num}">{mapped_num}</a></sup>'
        return match.group(0)
        
    return re.sub(r'\[(\d+)\]', repl, text)

# Helper function to render sources grid
def render_sources_grid(citations):
    if not citations:
        return
        
    seen = set()
    unique_cites = []
    for cite in citations:
        key = (cite["source_document"], cite["page_number"])
        if key not in seen:
            seen.add(key)
            unique_cites.append(cite)
            
    cards_html = '<div style="display: flex; gap: 12px; overflow-x: auto; padding-bottom: 12px; margin-bottom: 16px;">'
    for idx, cite in enumerate(unique_cites):
        doc_name = cite["source_document"]
        short_name = doc_name.replace("PC11_PCA_Data_Highlights_", "").replace(".md", "").replace(".pdf", "")
        snippet_escaped = cite["snippet"].replace('"', '&quot;').replace('\n', ' ')
        
        cards_html += f"""
        <div title="Snippet: {snippet_escaped}" style="background-color: #202222; border: 1px solid #2d3030; border-radius: 8px; padding: 10px 12px; min-width: 170px; max-width: 210px; flex-shrink: 0; display: flex; flex-direction: column; justify-content: space-between; height: 75px; box-shadow: 0 2px 5px rgba(0,0,0,0.2);">
            <div style="font-size: 0.85rem; font-weight: 600; color: #e3e3e3; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{short_name}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                <div style="font-size: 0.75rem; color: #8a8f98;">p. {cite['page_number']}</div>
                <div style="background-color: #2d3030; color: #13c2c2; font-size: 0.75rem; font-weight: bold; border-radius: 50%; width: 18px; height: 18px; display: flex; align-items: center; justify-content: center;">{idx+1}</div>
            </div>
        </div>
        """
    cards_html += '</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

# Initialize session state variables
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Fetch health status
try:
    health_resp = requests.get(f"{BACKEND_URL}/api/health", timeout=3)
    backend_connected = (health_resp.status_code == 200)
    health_data = health_resp.json()
except Exception:
    backend_connected = False
    health_data = {}

# Sidebar Configuration
with st.sidebar:
    st.markdown("<div style='padding: 10px 0px; text-align: center;'><h2 style='color: #ffffff; font-weight: 800; font-size: 1.5rem;'>perplexity census</h2></div>", unsafe_allow_html=True)
    
    # Model Selection
    model_option = st.selectbox(
        "Reasoning Model",
        options=["gpt-oss-120b", "zai-glm-4.7"],
        index=0
    )
    
    st.markdown("---")
    
    # New Chat Button
    if st.button("➕ New Chat", use_container_width=True):
        try:
            requests.delete(f"{BACKEND_URL}/api/history/{st.session_id}")
        except Exception:
            pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.toast("New chat session started!")
        st.rerun()
        
    st.markdown("---")
    
    # Connection status indicator
    if backend_connected:
        st.markdown("<div style='font-size: 0.85rem; color: #2ecc71;'>🟢 Connected to Backend API</div>", unsafe_allow_html=True)
        if health_data.get("database_connected"):
            st.markdown("<div style='font-size: 0.8rem; color: #8a8f98;'>· Database index: Ready</div>", unsafe_allow_html=True)
        if health_data.get("master_dataset_ready"):
            st.markdown("<div style='font-size: 0.8rem; color: #8a8f98;'>· Master CSV: Ready</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='font-size: 0.85rem; color: #e74c3c;'>🔴 Backend API Offline</div>", unsafe_allow_html=True)

# Process query helper
def process_query(prompt_text):
    if not prompt_text.strip():
        return
        
    st.session_state.messages.append({"role": "user", "answer": prompt_text})
    
    if not backend_connected:
        st.session_state.messages.append({
            "role": "assistant",
            "answer": "Cannot process message: FastAPI Backend is offline.",
            "citations": [],
            "artifacts": [],
            "logs": []
        })
        return
        
    try:
        payload = {
            "message": prompt_text,
            "session_id": st.session_state.session_id,
            "model": model_option
        }
        resp = requests.post(f"{BACKEND_URL}/api/chat", json=payload)
        
        if resp.status_code == 200:
            data = resp.json()
            st.session_state.messages.append({
                "role": "assistant",
                "answer": data["answer"],
                "citations": data["citations"],
                "artifacts": data["artifacts"],
                "logs": data["logs"]
            })
        else:
            st.session_state.messages.append({
                "role": "assistant",
                "answer": f"Error {resp.status_code}: {resp.text}",
                "citations": [],
                "artifacts": [],
                "logs": []
            })
    except Exception as e:
        st.session_state.messages.append({
            "role": "assistant",
            "answer": f"Failed to communicate with agent: {e}",
            "citations": [],
            "artifacts": [],
            "logs": []
        })

# Load history from backend on startup
if backend_connected and not st.session_state.messages:
    try:
        hist_resp = requests.get(f"{BACKEND_URL}/api/history/{st.session_id}")
        if hist_resp.status_code == 200:
            past_msgs = hist_resp.json()
            for msg in past_msgs:
                role = msg["role"]
                content = msg["content"]
                
                if role == "assistant" and isinstance(content, str) and content.strip().startswith("{"):
                    try:
                        parsed = json.loads(content)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "answer": parsed.get("answer", ""),
                            "citations": parsed.get("citations", []),
                            "artifacts": parsed.get("artifacts", []),
                            "logs": []
                        })
                    except Exception:
                        st.session_state.messages.append({
                            "role": "assistant",
                            "answer": content,
                            "citations": [],
                            "artifacts": [],
                            "logs": []
                        })
                else:
                    st.session_state.messages.append({
                        "role": role,
                        "answer": content
                    })
    except Exception as e:
        print(f"Error loading initial history: {e}")

# Landing Page View (when chat is empty)
if not st.session_state.messages:
    st.markdown("<div style='text-align: center; margin-top: 100px; margin-bottom: 25px;'><h1 style='font-size: 3.5rem; font-weight: 800; color: #ffffff; letter-spacing: -1px;'>Where knowledge begins.</h1><p style='color: #8a8f98; font-size: 1.1rem; margin-top: -10px;'>Ask anything about Census 2011 (Karnataka, Odisha, Madhya Pradesh)</p></div>", unsafe_allow_html=True)
    
    # Center input card container
    col_l, col_c, col_r = st.columns([1, 10, 1])
    with col_c:
        # We wrap in a container
        with st.container():
            landing_prompt = st.text_input("Ask anything...", key="landing_input", label_visibility="collapsed", placeholder="Ask anything about population, literacy, sex ratios...")
            if landing_prompt:
                with st.spinner("Analyzing sources and executing logic..."):
                    process_query(landing_prompt)
                st.rerun()
                
        # Suggestion pills below
        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
        cols = st.columns(4)
        suggestions = [
            ("📊 Compare Districts", "Show me a comparison of literacy rates in Belgaum vs Bangalore Rural in Karnataka."),
            ("👩‍🌾 Worker Stats", "What is the breakdown of main workers vs marginal workers in Odisha?"),
            ("📈 MP Growth Chart", "Show a chart comparing population growth rate of Indore, Bhopal, and Jabalpur in MP."),
            ("❓ Highest Sex Ratio", "Which district had the highest sex ratio in Karnataka, and what was it?")
        ]
        for idx, (label, prompt_text) in enumerate(suggestions):
            with cols[idx % 4]:
                if st.button(label, key=f"sug_{idx}", use_container_width=True):
                    with st.spinner("Analyzing sources and executing logic..."):
                        process_query(prompt_text)
                    st.rerun()

# Search Results View
else:
    # Render chat logs
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "user":
                st.markdown(f"<div style='font-size: 1.45rem; font-weight: 700; color: #ffffff; margin-bottom: 5px;'>{message['answer']}</div>", unsafe_allow_html=True)
            else:
                # 1. Sources Grid
                if message.get("citations"):
                    st.markdown("<div style='font-size: 0.8rem; font-weight: 600; color: #8a8f98; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;'>📚 Sources</div>", unsafe_allow_html=True)
                    render_sources_grid(message["citations"])
                
                # 2. Answer Heading and content
                st.markdown("<div style='font-size: 0.8rem; font-weight: 600; color: #8a8f98; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;'>📝 Answer</div>", unsafe_allow_html=True)
                formatted_answer = format_superscripts(message["answer"], message.get("citations", []))
                st.markdown(formatted_answer, unsafe_allow_html=True)
                
                # 3. Render inline artifacts if generated
                if message.get("artifacts"):
                    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
                    st.markdown("<div style='font-size: 0.8rem; font-weight: 600; color: #8a8f98; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px;'>📦 Generated Artifacts</div>", unsafe_allow_html=True)
                    for art in message["artifacts"]:
                        art_name = art["name"]
                        art_type = art["type"]
                        art_desc = art["description"]
                        
                        if art_type == "image":
                            image_url = f"{BACKEND_URL}/api/artifacts/{art_name}"
                            st.image(image_url, caption=f"{art_name}: {art_desc}", use_column_width=True)
                        elif art_type == "table" or art_name.endswith((".md", ".txt")):
                            try:
                                file_resp = requests.get(f"{BACKEND_URL}/api/artifacts/{art_name}")
                                if file_resp.status_code == 200:
                                    st.info(f"📄 **{art_name}**: {art_desc}")
                                    st.markdown(file_resp.text)
                            except Exception:
                                st.caption(f"Table artifact: [{art_name}]({BACKEND_URL}/api/artifacts/{art_name})")
                        else:
                            st.caption(f"Artifact generated: [{art_name}]({BACKEND_URL}/api/artifacts/{art_name}) ({art_desc})")
                            
                # 4. Citations Detailed expander
                if message.get("citations"):
                    with st.expander("🔍 Citations details", expanded=False):
                        for idx, cite in enumerate(message["citations"]):
                            st.markdown(
                                f"<div class='citation-box'>"
                                f"<strong>Source {idx+1}: {cite['source_document']} (Page {cite['page_number']})</strong><br/>"
                                f"<em>\"{cite['snippet']}\"</em>"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            
                # 5. Render trace logs for transparency
                if message.get("logs"):
                    with st.expander("⚙️ Agent execution trace", expanded=False):
                        log_text = "\n".join(message["logs"])
                        st.markdown(f"<pre class='log-box'>{log_text}</pre>", unsafe_allow_html=True)

    # Accept user follow-up input
    if follow_up := st.chat_input("Ask a follow-up..."):
        with st.chat_message("user"):
            st.markdown(f"<div style='font-size: 1.45rem; font-weight: 700; color: #ffffff; margin-bottom: 5px;'>{follow_up}</div>", unsafe_allow_html=True)
            
        st.session_state.messages.append({"role": "user", "answer": follow_up})
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking and executing logic..."):
                process_query(follow_up)
            st.rerun()
