import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import time
import re

# 1. Page Configuration & Elite Startup Stylesheet
st.set_page_config(page_title="Create a Tree", page_icon="🌳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Hide default Streamlit chrome for a native app feel */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Deep dark aesthetic with Inter font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #050505; color: #ededed; font-family: 'Inter', sans-serif; }
    
    /* Gradient Typography */
    .gradient-text {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; letter-spacing: -1.5px; margin-bottom: 0.2rem;
    }
    .sub-text { color: #8b949e; font-size: 1.1rem; margin-bottom: 2rem; }
    .gina-nod { color: #8b949e; font-style: italic; opacity: 0.8; }
    
    /* Glassmorphism Workspace Card */
    .glass-card {
        background: rgba(20, 20, 25, 0.4);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px; padding: 2rem; margin-bottom: 25px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }
    
    /* Input Styling */
    .stTextArea textarea {
        background-color: rgba(10, 10, 12, 0.8) !important; color: #e6edf3 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 10px !important;
        font-size: 14px; transition: all 0.3s ease;
    }
    .stTextArea textarea:focus {
        border-color: #4facfe !important; box-shadow: 0 0 0 2px rgba(79, 172, 254, 0.2) !important;
    }
    
    /* Premium Glowing Button */
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%) !important;
        color: #000000 !important; border: none !important;
        padding: 16px 40px !important; border-radius: 30px !important;
        font-weight: 700 !important; font-size: 1.1rem !important; letter-spacing: 0.5px;
        box-shadow: 0 4px 20px rgba(79, 172, 254, 0.3) !important; transition: all 0.3s ease !important; width: 100%;
    }
    div.stButton > button:first-child:hover {
        transform: translateY(-2px) !important; box-shadow: 0 8px 30px rgba(79, 172, 254, 0.5) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="gradient-text">Create a Tree</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Creator search. <span class="gina-nod">Built for Gina—with a little ginger magic. ✨</span></div>', unsafe_allow_html=True)

# 2. Securely fetch API Keys
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 Missing Gemini API Key in Streamlit Secrets.")
    st.stop()

# 3. Phase 1: Context Input Hub
st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    brand_context = st.text_area(
        "🏷️ Brand Profile & Identity Context",
        placeholder="e.g., A premium B2B SaaS platform targeting independent agencies...",
        height=120
    )

with col2:
    campaign_brief = st.text_area(
        "🎯 Campaign Goal & Creator Profile",
        placeholder="e.g., UK-based micro-creators sharing AI workflow tutorials...",
        height=120
    )

# Advanced Tuning Expander
with st.expander("⚙️ Advanced Search Tuning"):
    param_col1, param_col2 = st.columns(2)
    with param_col1:
        profile_count = st.slider("Maximum Profiles to Target", min_value=5, max_value=150, value=20, step=5)
    with param_col2:
        selected_platforms = st.multiselect("Target Networks", options=["Instagram", "TikTok"], default=["Instagram", "TikTok"])

st.markdown("</div>", unsafe_allow_html=True)

if "discovered_creators" not in st.session_state:
    st.session_state.discovered_creators = []

if st.button("🚀 Initialize Discovery Engine", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first.")
    elif not selected_platforms:
        st.warning("Please select at least one target social platform.")
    else:
        platform_str = " and ".join(selected_platforms) if len(selected_platforms) == 2 else f"exclusively {selected_platforms[0]}"
        
        try:
            with st.spinner("🌐 Traversing live global metadata index..."):
                iterations = 1 if profile_count <= 15 else (2 if profile_count <= 50 else 3)
                
                query_generation_prompt = f"""
                Based on this brand context: '{brand_context}' and campaign target: '{campaign_brief}', write exactly {iterations} distinct, plain-English search phrases designed to find individual, real UK-based creators on {platform_str}.
                Output ONLY the raw search phrases, one per line. No quotes.
                """
                query_res = client.models.generate_content(model='gemini-2.5-flash', contents=query_generation_prompt)
                search_queries = [q.strip() for q in query_res.text.split("\n") if q.strip()][:iterations]
                
                if not search_queries:
                    search_queries = [f"UK {platform_str} creators for {campaign_brief}"]

                aggregated_search_text = ""
                raw_verified_links = []
                
                for query in search_queries:
                    for attempt in range(3):
                        try:
                            search_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=f"Find individual {platform_str} profile web pages in the UK matching: {query}. Provide their names and follower sizes if mentioned.",
                                config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.3)
                            )
                            
                            if search_response.text:
                                aggregated_search_text += "\n" + search_response.text
                                
                            if search_response.candidates and search_response.candidates[0].grounding_metadata:
                                metadata = search_response.candidates[0].grounding_metadata
                                if metadata.grounding_chunks:
                                    for chunk in metadata.grounding_chunks:
                                        if chunk.web:
                                            url = chunk.web.uri or ""
                                            title = chunk.web.title or ""
                                            url_lower = url.lower()
                                            
                                            is_insta = "Instagram" in selected_platforms and "instagram.com" in url_lower
                                            is_tiktok = "TikTok" in selected_platforms and "tiktok.com" in url_lower
                                            
                                            if (is_insta or is_tiktok) and not any(x in url_lower for x in ["/p/", "/tag/", "/explore/", "directory", "search", "login"]):
                                                raw_verified_links.append({"url": url, "title": title})
                            break
                        except Exception as e:
                            if "503" in str(e) and attempt < 2:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                break

                if aggregated_search_text:
                    found_urls = re.findall(r'(https?://[^\s()<>\"\']+)', aggregated_search_text)
                    for link in found_urls:
                        link_lower = link.lower()
                        is_insta = "Instagram" in selected_platforms and "instagram.com" in link_lower
                        is_tiktok = "TikTok" in selected_platforms and "tiktok.com" in link_lower
                        
                        if (is_insta or is_tiktok) and not any(x in link_lower for x in ["/p/", "/tag/", "/explore/", "directory", "search", "login"]):
                            cleaned_link = link.strip(".,;:()[]{}'\"")
                            raw_verified_links.append({"url": cleaned_link, "title": "Discovered Creator"})

            if raw_verified_links:
                unique_sources = {v['url']: v for v in raw_verified_links}.values()
                source_pool = list(unique_sources)[:profile_count]
                
                with st.spinner(f"⚡ Synthesizing {len(source_pool)} verified data nodes..."):
                    format_prompt = f"""
                    You are a strict data parser. Log:
                    ---
                    {aggregated_search_text}
                    ---
                    Extract metrics ONLY for these verified links: {json.dumps(source_pool)}
                    Format as a JSON array of objects with keys: "Title", "Link", "Platform", "Followers (Est)", "Engagement Rate", "Snippet".
                    """
                    
                    for attempt in range(3):
                        try:
                            format_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=format_prompt,
                                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.1)
                            )
                            raw_json_data = format_response.text.strip() if format_response.text else ""
                            break
                        except Exception as e:
                            if "503" in str(e) and attempt < 2:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                raw_json_data = ""

                    json_match = re.search(r'\[.*\]', raw_json_data, re.DOTALL)
                    if json_match:
                        raw_json_data = json_match.group(0)
                        
                    raw_creators_list = []
                    try:
                        if raw_json_data:
                            raw_creators_list = json.loads(raw_json_data)
                    except json.JSONDecodeError:
                        pass 

                    normalized_list = []
                    if isinstance(raw_creators_list, list):
                        for item in raw_creators_list:
                            if not isinstance(item, dict):
                                continue
                            
                            url = str(item.get("Link", item.get("link", item.get("url", "")))).strip()
                            url_lower = url.lower()
                            
                            is_insta = "instagram.com" in url_lower
                            is_tiktok = "tiktok.com" in url_lower
                            
                            if is_insta or is_tiktok:
                                url = url.strip(".,;:()[]{}'\"")
                                normalized_item = {
                                    "Title": str(item.get("Title", item.get("title", "@Profile"))),
                                    "Link": url,
                                    "Platform": "Instagram" if is_insta else "TikTok",
                                    "Followers (Est)": str(item.get("Followers (Est)", "N/A")),
                                    "Engagement Rate": str(item.get("Engagement Rate", "N/A")),
                                    "Snippet": str(item.get("Snippet", "Verified entity."))
                                }
                                normalized_list.append(normalized_item)
                    
                    if normalized_list:
                        df_results = pd.DataFrame(normalized_list).drop_duplicates(subset=["Link"])
                        st.session_state.discovered_creators = df_results.to_dict('records')
                        st.toast('Extraction sequence complete.', icon='✅')
                    else:
                        st.warning("Data footprints located, but clean entity routing failed. Adjust parameters.")
            else:
                st.warning("No direct live profile links captured. Broaden campaign terms.")
                
        except Exception as e:
            st.error("Engine sequence interrupted. Please re-initialize.")

# 4. Phase 2: Interactive Data Workspace
if st.session_state.discovered_creators:
    st.write("---")
    st.markdown("### 📊 Intelligence Matrix")
    
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
        label="📥 Download Matrix (CSV)",
        data=csv,
        file_name="intelligence_matrix.csv",
        mime="text/csv",
    )
