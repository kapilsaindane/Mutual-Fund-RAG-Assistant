import os
import sys
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Add retrieval module to path
sys.path.insert(0, str(Path(__file__).resolve().parent / "retrieval"))
sys.path.insert(0, str(Path(__file__).resolve().parent / "retrieval" / "phase-5"))

from phase_5.orchestrator import Orchestrator

# Load environment variables
load_dotenv()

st.set_page_config(
    page_title="Mutual Fund FAQ Assistant",
    page_icon="💼",
    layout="centered"
)

@st.cache_resource
def get_orchestrator():
    use_groq = os.environ.get('USE_GROQ', 'true').lower() == 'true'
    groq_api_key = os.environ.get('GROQ_API_KEY')
    return Orchestrator(use_groq=use_groq, groq_api_key=groq_api_key)

# App UI
st.title("💼 Mutual Fund FAQ Assistant")
st.caption("Facts-only. No investment advice.")

# Example questions in the sidebar or expander
with st.sidebar:
    st.header("Example Questions")
    if st.button("What is expense ratio of SBI Bluechip Fund?"):
        st.session_state.example_query = "What is expense ratio of SBI Bluechip Fund?"
    if st.button("What is minimum SIP amount?"):
        st.session_state.example_query = "What is minimum SIP amount?"
    if st.button("What is the lock-in period?"):
        st.session_state.example_query = "What is the lock-in period?"

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "metadata" in message:
            meta = message["metadata"]
            if meta.get("source_url"):
                st.caption(f"Source: [{meta['source_url'].split('//')[-1]}]({meta['source_url']})")
            if meta.get("last_updated"):
                st.caption(f"Last updated from sources: {meta['last_updated']}")

# Get user input
prompt = st.chat_input("Ask a question about Mutual Funds...")

if hasattr(st.session_state, 'example_query'):
    prompt = st.session_state.example_query
    del st.session_state.example_query

if prompt:
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    orchestrator = get_orchestrator()

    with st.chat_message("assistant"):
        with st.spinner("Searching for factual answers..."):
            result = orchestrator.query(prompt)
            
            answer_text = result.get('response', "An error occurred.")
            ui_data = result.get('ui_data', {})
            
            st.markdown(answer_text)
            
            if ui_data.get('source_url'):
                source = ui_data['source_url']
                display_source = source.split('//')[-1]
                st.caption(f"Source: [{display_source}]({source})")
            if ui_data.get('last_updated'):
                st.caption(f"Last updated from sources: {ui_data['last_updated']}")
            
            # Add assistant response to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer_text,
                "metadata": ui_data
            })
