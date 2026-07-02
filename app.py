import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import time
import re

# 1. Page Configuration & Fluid Agency Theme Injection
st.set_page_config(page_title="Creator Funnel Finder", page_icon="🔍", layout="wide")

st.markdown("""
    <style>
    .stApp {
        background-color: #0b0e14;
        color: #e6edf3;
    }
    h1 {
        font-family: 'Inter', sans-serif;
        color: #ffffff;
        font-weight: 800;
        background: linear-gradient(135deg, #58a6ff 0%, #bc8cff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -1px;
        padding-bottom: 10px;
    }
    .workspace-card {
        background: linear-gradient(180deg, #161b22 0%, #0f1319 100%);
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #30363d;
        margin-bottom: 25px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .stTextArea textarea {
        background-color: #0d1117 !important;
        color: #c9d1d9 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        font-size: 14px;
    }
    .stTextArea textarea:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 2px rgba(88,166,255,0.15) !important;
    }
    div.stButton > button:first-child {
        background: linear-gradient(135deg, #1f6feb 0%, #58a6ff 100%) !important;
        color: #ffffff !important;
        border: none !important;
        padding: 14px 35px !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        letter-spacing: 0.5px;
        box-shadow: 0 4px 15px rgba(31,111,235,0.25) !important;
        transition: all 0.2s ease !important;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(88,166,255,0.4) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🔍 Creator Funnel Finder")
st.write("Target specific brand profiles and campaign directives to extract verified creator networks.")
st.write("---")

# 2. Securely fetch API Keys from Streamlit Secrets
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 Missing Gemini API Key. Please ensure GEMINI_API_KEY is added to your Streamlit Secrets.")
    st.stop()

# 3. Phase 1: Context Input Hub
st.markdown("<div class='workspace-card'>", unsafe_allow_html=True)
st.markdown("### 📋 Campaign Workspace Setup")
col1, col2 = st.columns(2)

with col1:
    brand_context = st.text_area(
        "🏷️ Brand Profile & Identity Context:",
        placeholder="e.g., A premium, minimalist B2B platform that uses generative AI to help boutique creative agencies automate high-end visual design assets...",
        height=120
    )

with col2:
    campaign_brief = st.text_area(
        "🎯 Campaign Goal & Target Creator Vibe:",
        placeholder="e.g., Looking for UK-based digital artists or micro-creators on Instagram/TikTok sharing step-by-step Midjourney hacks or workflow secrets...",
        height=120
    )

# Parameters Row
param_col1, param_col2 = st.columns(2)

with param_col1:
    profile_count = st.slider(
        "📊 Maximum Profiles to Target:",
        min_value=5,
        max_value=150,
        value=20,
        step=5,
        help="Set the target upper limit of verified creators to gather across deep index sweeps."
    )

with param_col2:
    selected_platforms = st.multiselect(
        "📱 Target Social Platforms:",
        options=["Instagram", "TikTok"],
        default=["Instagram", "TikTok"],
        help="Select one or both networks to isolate discovery paths."
    )
st.markdown("</div>", unsafe_allow_html=True)

if "discovered_creators" not in st.session_state:
    st.session_state.discovered_creators = []

if st.button("🚀 Discover Matched Creators", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first!")
    elif not selected_platforms:
        st.warning("Please select at least one target social platform!")
    else:
        platform_str = " and ".join(selected_platforms) if len(selected_platforms) == 2 else f"exclusively {selected_platforms[0]}"
        
        try:
            # --- STAGE 1: LIVE SEARCH ENGINE DEEP GROUNDING CRAWL ---
            with st.spinner("🌐 Executing multi-stage index sweep across live Google Search metadata..."):
                # Determine loop iterations based on scale selection to protect deep link harvesting
                iterations = 1 if profile_count <= 15 else (2 if profile_count <= 50 else 3)
                
                # Dynamic Query Builder Loop
                query_generation_prompt = f"""
                Based on this brand context: '{brand_context}' and campaign target: '{campaign_brief}', write exactly {iterations} distinct, highly optimized Google X-ray search strings targeting individual creator profile directories on {platform_str} in the UK.
                Output ONLY the raw search strings, one per line. No introduction text, no quotation marks.
                """
                query_res = client.models.generate_content(model='gemini-2.5-flash', contents=query_generation_prompt)
                search_queries = [q.strip() for q in query_res.text.split("\n") if q.strip()][:iterations]
                
                if not search_queries:
                    search_queries = [f"site:instagram.com UK creator {campaign_brief}"]

                aggregated_search_text = ""
                raw_verified_links = []
                
                # Execute consecutive search passes
                for query in search_queries:
                    for attempt in range(3):
                        try:
                            search_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=f"Locate direct, individual creator profile links matching this query: {query}. Compile their handles, estimated follower data, and content descriptions.",
                                config=types.GenerateContentConfig(
                                    tools=[types.Tool(google_search=types.GoogleSearch())],
                                    temperature=0.2
                                )
                            )
                            
                            if search_response.text:
                                aggregated_search_text += "\n" + search_response.text
                                
                            # Metadata Harvesting Layer: Extract absolute verified links directly from Google's database packets
                            if search_response.candidates and search_response.candidates[0].grounding_metadata:
                                metadata = search_response.candidates[0].grounding_metadata
                                if metadata.grounding_chunks:
                                    for chunk in metadata.grounding_chunks:
                                        if chunk.web:
                                            url = chunk.web.uri or ""
                                            title = chunk.web.title or ""
                                            url_lower = url.lower()
                                            
                                            is_insta = "Instagram" in selected_platforms and "[instagram.com/](https://instagram.com/)" in url_lower
                                            is_tiktok = "TikTok" in selected_platforms and "[tiktok.com/](https://tiktok.com/)" in url_lower
                                            
                                            if (is_insta or is_tiktok) and not any(x in url_lower for x in ["/p/", "/tag/", "/explore/", "directory", "search"]):
                                                raw_verified_links.append({"url": url, "title": title})
                            break
                        except Exception as e:
                            if "503" in str(e) and attempt < 2:
                                time.sleep(2)
                                continue
                            else:
                                break

            # --- STAGE 2: STRICT DATA MAPPING FROM LIVE METADATA ONLY ---
            if raw_verified_links and aggregated_search_text:
                # Deduplicate links via Python side dictionary validation before mapping
                unique_sources = {v['url']: v for v in raw_verified_links}.values()
                source_pool = list(unique_sources)[:profile_count]
                
                with st.spinner(f"📊 Filtering and mapping {len(source_pool)} authentic creator profiles into data hub..."):
                    format_prompt = f"""
                    You are a data formatting specialist. Review this text database containing creator profiles and search data:
                    ---
                    {aggregated_search_text}
                    ---
                    
                    Your exact job is to extract data ONLY for these verified profile links:
                    {json.dumps(source_pool)}
                    
                    CRITICAL ZERO-HALLUCINATION RULES:
                    1. You are strictly forbidden from creating handles or usernames.
                    2. Only output data rows for the links provided in the verified link list above. If a link isn't in that list, ignore it completely.
                    
                    Format the output into a clean JSON array of objects, where each object has these keys:
                    "Title": Clean creator name or handle extracted from the text/title.
                    "Link": The unedited matching profile URL from the verified list.
                    "Platform": Must be exactly 'Instagram' or 'TikTok'.
                    "Followers (Est)": Look closely at the text database to extract their actual follower count (e.g., '12K', '85K', or 'N/A').
                    "Engagement Rate": Estimate a baseline percentage benchmark for their follower tier or 'N/A'.
                    "Snippet": A brief sentence on why they fit this specific campaign setup.
                    """
                    
                    format_response = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=format_prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    
                    raw_json_data = format_response.text.strip() if format_response.text else ""
                    
                    # Regex sanitizer safeguard if markdown blocks leak through
                    if "```" in raw_json_data:
                        raw_json_data = re.sub(r'^```[a-zA-Z]*\n|```$', '', raw_json_data, flags=re.MULTILINE).strip()
                    
                    if raw_json_data:
                        raw_creators_list = json.loads(raw_json_data)
                        
                        normalized_list = []
                        for item in raw_creators_list:
                            url = str(item.get("Link", item.get("link", item.get("url", "")))).strip()
                            url_lower = url.lower()
                            
                            # Double check platform alignment
                            is_insta = "instagram.com" in url_lower
                            is_tiktok = "tiktok.com" in url_lower
                            
                            if is_insta or is_tiktok:
                                if url.endswith(".") or url.endswith(","):
                                    url = url[:-1]
                                    
                                normalized_item = {
                                    "Title": item.get("Title", item.get("title", "@Profile")),
                                    "Link": url,
                                    "Platform": "Instagram" if is_insta else "TikTok",
                                    "Followers (Est)": item.get("Followers (Est)", "N/A"),
                                    "Engagement Rate": item.get("Engagement Rate", "N/A"),
                                    "Snippet": item.get("Snippet", "Live verified search match.")
                                }
                                normalized_list.append(normalized_item)
                        
                        if normalized_list:
                            df_results = pd.DataFrame(normalized_list).drop_duplicates(subset=["Link"])
                            st.session_state.discovered_creators = df_results.to_dict('records')
                            st.success(f"🎉 Successfully verified and loaded {len(df_results)} authentic creator profiles!")
                        else:
                            st.warning("Google found data footprints, but could not secure clean individual user routings. Try altering parameters.")
                    else:
                        st.error("The formatting infrastructure hit an extraction failure.")
            else:
                st.warning("No direct live profile links were caught in the initial metadata sweeps. Try broadening the campaign terms.")
                
        except Exception as e:
            st.error(f"An error occurred during discovery: {str(e)}")

# 4. Phase 2: Interactive Data Workspace Hub
if st.session_state.discovered_creators:
    st.write("---")
    st.markdown("### 📋 Discovered Profiles & Data Hub")
    st.info("💡 Pro-Tip: You can double-click inside cells to manually type metrics directly from your open links.")
    
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    
    cols = ["Title", "Link", "Platform", "Followers (Est)", "Engagement Rate", "Snippet"]
    df_display = df_display.reindex(columns=[c for c in cols if c in df_display.columns])

    edited_df = st.data_editor(
        df_display,
        column_config={
            "Link": st.column_config.LinkColumn("Profile URL"),
            "Followers (Est)": st.column_config.TextColumn("Followers (Est)"),
            "Engagement Rate": st.column_config.TextColumn("Engagement Rate"),
        },
        disabled=["Title", "Link", "Platform", "Snippet"],
        hide_index=True,
        width="stretch"
    )
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Selected Creators to CSV",
        data=csv,
        file_name="discovered_creators.csv",
        mime="text/csv",
    )
