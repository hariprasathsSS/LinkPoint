import streamlit as st
import requests

st.set_page_config(
    page_title="AKIRA Claims Assistant",
    page_icon="🛡️",
    layout="centered"
)

# Premium Color Palette & CSS
st.markdown("""
<style>
    /* Main Background & Text */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Header/Title */
    h1 {
        color: #e6edf3 !important;
        font-weight: 600 !important;
        text-align: center;
        margin-bottom: -10px;
    }
    
    /* Caption */
    .st-emotion-cache-1629p8f p, .st-emotion-cache-1104ytp p {
        color: #8b949e !important;
        text-align: center;
    }

    /* Chat Messages */
    .stChatMessage {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
    }
    
    /* Assistant vs User distinction can be done via data-testid if needed, 
       but Streamlit handles icons nicely out of the box */

    /* Input Box */
    .stChatInputContainer {
        border-radius: 20px !important;
        border: 1px solid #58a6ff !important;
        background-color: #0d1117 !important;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #238636;
        color: #ffffff;
        border: none;
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ AKIRA")
st.caption("Premium Claims Intelligence & Database Search")

API_URL = "http://127.0.0.1:8003/chat"

def render_md(text: str) -> str:
    """Escape $ so Streamlit doesn't interpret currency amounts as LaTeX math."""
    return (text or "").replace("\\$", "$").replace("$", "\\$")


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Welcome to AKIRA. I can search claims by customer name, peril, status, and answer complex policy questions. How can I help?"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(render_md(message["content"]))

if prompt := st.chat_input("E.g., Find claims for Alice Smith, or Is water damage covered?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(render_md(prompt))

    with st.chat_message("assistant"):
        with st.spinner("AKIRA is thinking..."):
            try:
                response = requests.post(
                    API_URL, 
                    json={"message": prompt, "mode": "multi"}
                )
                response.raise_for_status()
                answer = response.json().get("answer", "No answer returned.")
                st.markdown(render_md(answer))
                st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"Error communicating with backend: {e}")
