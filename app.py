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
st.markdown('<div class="sub-text">Hyper-Accurate Sourcing Engine. Optimized for Verified Public Profiles. ✨</div>', unsafe_allow_html=True)

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
    """Extracts rows from a standard markdown text table and outputs a clean DataFrame."""
    lines = [line.strip() for line in markdown_text.split('\n') if line.strip()]
    table_lines = [line for line in lines if line.startswith('|') and line.endswith('|')]
    
    if len(table_lines) < 2:
        return None
        
    headers = [cell.strip() for cell in table_lines[0].split('|')[1:-1]]
    rows = []
    
    for line in table_lines[1:]:
        if '-' in line and line.count('-') > 3:
            continue
        cells = [cell.strip() for cell in line.split('|')[1:-1]]
        if len(cells) == len(headers):
            rows.append(cells)
            
    if not rows:
        return None
    return pd.DataFrame(rows, columns=headers)

if st.button("🚀 Initialize Discovery Engine", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first.")
    elif not selected_platforms:
        st.warning("Please select at least one target social network platform.")
    else:
        with st.status("Executing public authentication & query layers...", expanded=True) as status:
            platforms_str = " or ".join(selected_platforms)
            mega_prompt = f"""
            Act as an elite, hyper-focused talent scout specializing in high-fidelity niche influencer discovery.
            Brand Identity/Vibe: {brand_context}
            Specific Sourcing Target: {campaign_brief}
            Target Networks: Only fetch accounts on {platforms_str}
            Follower Size Guardrail: {follower_target}
            Required List Count: Exactly {profile_count} individual creators.
            
            STRICT ACCURACY & ACCESSIBILITY STRATEGY:
            1. BANNED: Do not pull generic global influencers, automated meme curation channels, or copy high-level names from generic online listicles.
            2. PUBLIC ACCOUNTS ONLY: Every single profile included must be a public creator page. Carefully evaluate the search snippet metadata. If there is any indication that an account is private, locked, invitation-only, or inactive (e.g., 0 posts), you MUST discard it immediately and find an open option.
            3. REGIONALITY: Explicitly restrict searches to creators based inside the United Kingdom.
            4. DIRECT PROFILING: Construct or pull the clean, direct absolute profile URL for every target (e.g., https://www.instagram.com/username or https://www.tiktok.com/@username). 
            5. RELEVANCE PROOF: For every single account, you must explicitly state exactly WHAT real-world niche utility or specific workflow footage they share that directly ties them to the campaign goals. If you cannot provide a clear proof statement for a profile, discard it.
            
            Output strictly as a Markdown table using this layout:
            | Creator Handle | Direct Profile Link | Platform | Followers (Est) | Total Posts | Niche Focus / Proof |
            
            For Total Posts and Followers, look at the indexed text strings; if missing or ambiguous, write "N/A (Manual Entry)". Do not include any pre-text or conversational summaries. Just return the structured table.
            """
            
            try:
                res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=mega_prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.1
                    )
                )
                
                df = parse_markdown_table(res.text)
                if df is not None and not df.empty:
                    st.session_state.discovered_creators = df.to_dict('records')
                    status.update(label=f"Successfully verified and locked {len(df)} active public creators!", state="complete")
                else:
                    status.update(label="Failed to parse clean layout. Retrying criteria...", state="error")
                    st.write("Raw Output Logs:")
                    st.write(res.text)
            except Exception as e:
                status.update(label=f"Engine error: {str(e)}", state="error")

if st.session_state.discovered_creators:
    st.write("---")
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    
    # Render interactive data editor interface matching the exact prompt keys
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
