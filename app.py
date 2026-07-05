import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import re

# 1. Page Configuration & Startup Layout
st.set_page_config(page_title="Creator Tree", page_icon="🌳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #050505; color: #ededed; font-family: 'Inter', sans-serif; }
    .gradient-text {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; letter-spacing: -1.5px; margin-bottom: 0.2rem;
    }
    .sub-text { color: #8b949e; font-size: 1.1rem; margin-bottom: 2rem; }
    .glass-card {
        background: rgba(20, 20, 25, 0.4); backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 2rem; margin-bottom: 25px;
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
        color: #000000 !important; border: none !important;
        padding: 16px 40px !important; border-radius: 30px !important;
        font-weight: 700 !important; font-size: 1.1rem !important; width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="gradient-text">Creator Tree</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Native Search Edition. Built for Gina. ✨</div>', unsafe_allow_html=True)

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception as e:
    st.error("🔑 Setup Missing: Ensure GEMINI_API_KEY is configured in Streamlit Secrets.")
    st.stop()

st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
with col1:
    brand_context = st.text_area("🏷️ Brand Profile & Identity Context", height=120)
with col2:
    campaign_brief = st.text_area("🎯 Campaign Goal & Creator Profile", height=120)

with st.expander("⚙️ Advanced Tuning", expanded=True):
    param_col1, param_col2 = st.columns(2)
    with param_col1:
        profile_count = st.slider("Profiles to Target", min_value=5, max_value=50, value=20, step=5)
    with param_col2:
        follower_target = st.text_input("👥 Target Follower Range", placeholder="e.g., 10K - 50K")
st.markdown("</div>", unsafe_allow_html=True)

if "discovered_creators" not in st.session_state: st.session_state.discovered_creators = []

if st.button("🚀 Initialize Discovery Engine", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first.")
    else:
        with st.status("Assembling creator matrix...", expanded=True) as status:
            mega_prompt = f"""
            Act as an expert researcher. 
            Brand Context: {brand_context}
            Goal: {campaign_brief}
            Target Followers: {follower_target}
            
            Task:
            1. Use your integrated Google Search tool to find genuine UK-based creator profiles on Instagram or TikTok matching this vibe.
            2. Extract exactly: Title, Link, Platform, Followers (Est), Following Count, Total Posts.
            3. If a specific metric isn't explicitly visible in your search results, populate it with "N/A (Manual Entry)". Do not guess numbers.
            4. Return the results ONLY as a valid raw JSON array of objects inside markdown code brackets. Do not wrap it in prose.
            """
            
            try:
                # Execution with Google Search tool enabled
                res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=mega_prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.0
                    )
                )
                
                # Robust extraction parsing via regex container matching
                json_match = re.search(r'\[.*\]', res.text, re.DOTALL)
                if json_match:
                    st.session_state.discovered_creators = json.loads(json_match.group(0))
                    status.update(label="Report ready!", state="complete")
                else:
                    status.update(label="Data formatting failed.", state="error")
                    st.write("Raw Engine Logs:")
                    st.code(res.text)
            except Exception as e:
                status.update(label=f"Engine error: {str(e)}", state="error")

if st.session_state.discovered_creators:
    st.write("---")
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    edited_df = st.data_editor(df_display, width="stretch", hide_index=True)
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Report (CSV)", csv, "creator_report.csv", "text/csv")
