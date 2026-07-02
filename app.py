import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import time
import re
import random

# 1. Page Configuration
st.set_page_config(page_title="Creator Tree", page_icon="🌳", layout="wide", initial_sidebar_state="collapsed")

# 2. Styling
st.markdown("""
    <style>
    .gradient-text { background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.8rem; }
    .sub-text { color: #8b949e; font-size: 1.1rem; margin-bottom: 2rem; }
    .glass-card { background: rgba(20, 20, 25, 0.4); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="gradient-text">Creator Tree</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Creator search. <span>Built for Gina. ✨</span></div>', unsafe_allow_html=True)

# 3. Robust API Handler (With Jitter & Backoff)
def safe_api_call(client, prompt, config=None):
    for attempt in range(5):
        try:
            return client.models.generate_content(model='gemini-2.5-flash', contents=prompt, config=config)
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "503" in err_msg:
                wait_time = 10 + (attempt * 5) + random.randint(1, 3)
                time.sleep(wait_time)
                continue
            else:
                st.error(f"API Error: {err_msg}")
                return None
    return None

# API Setup
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Missing Gemini API Key in Secrets.")
    st.stop()

# Inputs
st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
brand_context = col1.text_area("Brand Context", height=100)
campaign_brief = col2.text_area("Campaign Goal", height=100)
follower_target = st.text_input("Follower Range", placeholder="e.g., 10K - 50K")
profile_count = st.slider("Max Profiles", 5, 150, 20, 5)
st.markdown("</div>", unsafe_allow_html=True)

if "discovered_creators" not in st.session_state: st.session_state.discovered_creators = []

if st.button("🚀 Initialize Discovery Engine", type="primary"):
    raw_verified_dict = {}
    
    with st.spinner("Traversing index..."):
        # Generate search queries
        query_res = safe_api_call(client, f"Based on: {brand_context} and {campaign_brief}, write 10 distinct UK search phrases. Return ONE per line.")
        if query_res:
            queries = [q.strip() for q in query_res.text.split("\n") if q.strip()]
            
            for query in queries:
                if len(raw_verified_dict) >= profile_count: break
                
                # Execute Search
                res = safe_api_call(client, f"Find UK {query}. {follower_target}. Provide names, following count, total posts.", 
                                    config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
                
                if res and res.candidates and res.candidates[0].grounding_metadata:
                    for chunk in res.candidates[0].grounding_metadata.grounding_chunks:
                        if chunk.web and "instagram.com" in chunk.web.uri.lower() or "tiktok.com" in chunk.web.uri.lower():
                            url = chunk.web.uri.split('?')[0].strip("/")
                            raw_verified_dict[url] = {"url": url, "title": chunk.web.title}
                
                time.sleep(6 + random.uniform(1, 3)) # Pacing governor
        
        # Formatting
        source_pool = list(raw_verified_dict.values())[:profile_count]
        if source_pool:
            format_prompt = f"Extract into JSON array [Title, Link, Platform, Followers (Est), Following Count, Total Posts] for these: {json.dumps(source_pool)}"
            final_res = safe_api_call(client, format_prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
            
            if final_res:
                try:
                    data = json.loads(re.search(r'\[.*\]', final_res.text, re.DOTALL).group(0))
                    df = pd.DataFrame(data).drop_duplicates(subset=["Link"])
                    st.session_state.discovered_creators = df.to_dict('records')
                    st.toast("Report ready!")
                except: st.warning("Parsing failed, but data found. Please retry.")

if st.session_state.discovered_creators:
    st.write("---")
    df = pd.DataFrame(st.session_state.discovered_creators)
    edited_df = st.data_editor(df, width="stretch", hide_index=True)
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Report", csv, "creator_report.csv", "text/csv")
