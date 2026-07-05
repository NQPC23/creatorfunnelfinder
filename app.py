import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import re

# 1. Page Configuration & Elite Startup Stylesheet
st.set_page_config(page_title="Creator Tree", page_icon="🌳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght=400;600;800&display=swap');
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
st.markdown('<div class="sub-text">Iterative Deep-Search Matrix. Built for Gina. ✨</div>', unsafe_allow_html=True)

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
    param_col1, param_col2, param_col3 = st.columns(3)
    with param_col1:
        profile_count = st.slider("Profiles to Target", min_value=5, max_value=50, value=20, step=5)
    with param_col2:
        selected_platforms = st.multiselect("Target Networks", options=["Instagram", "TikTok"], default=["Instagram", "TikTok"])
    with param_col3:
        follower_target = st.text_input("👥 Target Follower Range", placeholder="e.g., 10K - 50K")
st.markdown("</div>", unsafe_allow_html=True)

if "discovered_creators" not in st.session_state: st.session_state.discovered_creators = []

def parse_markdown_table(markdown_text):
    """Extracts rows from a standard markdown text table and outputs a clean list of dicts."""
    lines = [line.strip() for line in markdown_text.split('\n') if line.strip()]
    table_lines = [line for line in lines if line.startswith('|') and line.endswith('|')]
    
    if len(table_lines) < 2:
        return []
        
    headers = [cell.strip() for cell in table_lines[0].split('|')[1:-1]]
    rows = []
    
    for line in table_lines[1:]:
        if '-' in line and line.count('-') > 3:
            continue
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
            
    return rows

if st.button("🚀 Initialize Discovery Engine", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first.")
    elif not selected_platforms:
        st.warning("Please select at least one target network platform.")
    else:
        # Segment search strategies into unique sub-batches to force fresh search queries
        if len(selected_platforms) == 2:
            sub_batches = [
                {"platform": "Instagram", "focus": "uk creators, indie hackers, setup vlogs"},
                {"platform": "TikTok", "focus": "uk tech tools, software development, coding tutorials"},
                {"platform": "Instagram", "focus": "uk ai automation, productivity systems, workflow optimization"}
            ]
        elif "Instagram" in selected_platforms:
            sub_batches = [
                {"platform": "Instagram", "focus": "uk indie hackers, tech builders, software engineering"},
                {"platform": "Instagram", "focus": "uk ai automation tools, productivity workflows"},
                {"platform": "Instagram", "focus": "uk software creators, technology setups, startup vlogs"}
            ]
        else:
            sub_batches = [
                {"platform": "TikTok", "focus": "uk tech tools, coding execution, developer life"},
                {"platform": "TikTok", "focus": "uk ai automation tutorials, prompt engineering"},
                {"platform": "TikTok", "focus": "uk software builders, tech setup optimization"}
            ]
            
        master_rows = []
        
        with st.status("Executing sequential batch intelligence loops...", expanded=True) as status:
            for i, batch in enumerate(sub_batches):
                status.update(label=f"Scanning Batch {i+1}/3 ({batch['platform']} - {batch['focus']})...", state="running")
                
                mega_prompt = f"""
                Act as an elite talent scout specializing in high-fidelity influencer discovery.
                Brand Identity: {brand_context}
                Sourcing Request: {campaign_brief}
                Target Network: {batch['platform']}
                Follower Size Guardrail: {follower_target}
                Specific Search Lens Focus: {batch['focus']}
                
                CRITICAL OPERATIONAL RULES:
                1. PUBLIC ACCOUNTS ONLY: Every profile included must be a public creator page. If there is any indication that an account is private, locked, or completely inactive, discard it immediately.
                2. REGIONALITY: Restrict profiles strictly to individuals located within the United Kingdom.
                3. DIRECT PROFILING: Provide the complete absolute profile URL link (e.g., https://www.instagram.com/username or https://www.tiktok.com/@username). Never output short-text markdown links like [Profile].
                4. RELEVANCE PROOF: You must explicitly state exactly WHAT real-world niche utility or specific project workflow they share that ties them directly to the goals.
                5. Extract exactly 7 unique, highly contextual profiles for this specific batch.
                
                Output strictly as a Markdown table using this layout:
                | Creator Handle | Direct Profile Link | Platform | Followers (Est) | Total Posts | Niche Focus / Proof |
                
                For metrics, read the indexed text string; if missing, write "N/A (Manual Entry)". Do not include pre-text or summaries.
                """
                
                try:
                    res = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=mega_prompt,
                        config=types.GenerateContentConfig(
                            tools=[types.Tool(google_search=types.GoogleSearch())],
                            temperature=0.2
                        )
                    )
                    
                    parsed_rows = parse_markdown_table(res.text)
                    if parsed_rows:
                        master_rows.extend(parsed_rows)
                except Exception as e:
                    st.sidebar.error(f"Batch {i+1} anomaly caught: {str(e)}")
                    continue
            
            if master_rows:
                df_results = pd.DataFrame(master_rows)
                # Safeguard: Clean and format data keys securely
                if "Direct Profile Link" in df_results.columns:
                    df_results = df_results.drop_duplicates(subset=["Direct Profile Link"])
                
                df_results = df_results.head(profile_count)
                st.session_state.discovered_creators = df_results.to_dict('records')
                status.update(label=f"Successfully compiled and deduplicated {len(df_results)} public creators!", state="complete")
            else:
                status.update(label="Sourcing loops returned empty matrices. Adjust tuning tags.", state="error")

if st.session_state.discovered_creators:
    st.write("---")
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Direct Profile Link": st.column_config.LinkColumn("Profile URL"),
            "Niche Focus / Proof": st.column_config.TextColumn("Why They Match (Relevancy Filter)", width="large"),
        },
        width="stretch",
        hide_index=True
    )
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Filtered Report (CSV)", csv, "creator_report.csv", "text/csv")
