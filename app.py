import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import time
import re
import random

st.set_page_config(page_title="Creator Tree", page_icon="🌳", layout="wide")

st.markdown("""
    <style>
    .gradient-text { background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 2.8rem; }
    .glass-card { background: rgba(20, 20, 25, 0.4); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 16px; padding: 2rem; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="gradient-text">Creator Tree</div>', unsafe_allow_html=True)
st.markdown('*Built for Gina—with a little ginger magic. ✨*')

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except:
    st.error("Missing Gemini API Key.")
    st.stop()

st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
col1, col2 = st.columns(2)
brand_context = col1.text_area("Brand Context", height=100)
campaign_brief = col2.text_area("Campaign Goal", height=100)
follower_target = st.text_input("Follower Range", placeholder="e.g., 10K - 50K")
profile_count = st.slider("Max Profiles", 5, 50, 20, 5)
st.markdown("</div>", unsafe_allow_html=True)

if "discovered_creators" not in st.session_state: st.session_state.discovered_creators = []

if st.button("🚀 Initialize Discovery Engine", type="primary"):
    raw_verified_dict = {}
    
    # Use st.status for non-blocking UI feedback
    with st.status("Initializing engine...", expanded=True) as status:
        # Step 1: Generate Queries
        status.write("Generating targeted search phrases...")
        query_prompt = f"Based on: {brand_context} and {campaign_brief}, write 5 UK search phrases. Return ONE per line."
        query_res = client.models.generate_content(model='gemini-2.5-flash', contents=query_prompt)
        queries = [q.strip() for q in query_res.text.split("\n") if q.strip()]
        
        # Step 2: Loop with feedback
        for i, query in enumerate(queries):
            if len(raw_verified_dict) >= profile_count: break
            status.update(label=f"Traversing index: {i+1}/{len(queries)}...", state="running")
            
            try:
                res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Find UK {query}. {follower_target}. Provide names, following count, total posts.",
                    config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                
                if res.candidates and res.candidates[0].grounding_metadata:
                    for chunk in res.candidates[0].grounding_metadata.grounding_chunks:
                        if chunk.web and ("instagram.com" in chunk.web.uri.lower() or "tiktok.com" in chunk.web.uri.lower()):
                            url = chunk.web.uri.split('?')[0].strip("/")
                            raw_verified_dict[url] = {"url": url, "title": chunk.web.title}
                
                time.sleep(5) # Strict 5s delay prevents 429 errors
            except Exception as e:
                status.write(f"Slowed down due to API limits. Retrying...")
                time.sleep(10)
        
        # Step 3: Parse Data
        status.update(label="Analyzing data patterns...", state="running")
        source_pool = list(raw_verified_dict.values())[:profile_count]
        
        if source_pool:
            format_prompt = f"Convert to JSON array [Title, Link, Platform, Followers (Est), Following Count, Total Posts] for: {json.dumps(source_pool)}"
            final_res = client.models.generate_content(model='gemini-2.5-flash', contents=format_prompt, config=types.GenerateContentConfig(response_mime_type="application/json"))
            
            try:
                data = json.loads(re.search(r'\[.*\]', final_res.text, re.DOTALL).group(0))
                st.session_state.discovered_creators = data
                status.update(label="Report Complete!", state="complete")
            except:
                status.update(label="Analysis failed.", state="error")
        else:
            status.update(label="No valid profiles found.", state="error")

if st.session_state.discovered_creators:
    df = pd.DataFrame(st.session_state.discovered_creators)
    st.data_editor(df, width="stretch", hide_index=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Report", csv, "creator_report.csv", "text/csv")
