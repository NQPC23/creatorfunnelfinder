import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import time
import re

# 1. Page Configuration & Elite Startup Stylesheet
st.set_page_config(page_title="Creator Tree", page_icon="🌳", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background-color: #050505; color: #ededed; font-family: 'Inter', sans-serif; }
    
    .gradient-text {
        background: linear-gradient(135deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; letter-spacing: -1.5px; margin-bottom: 0.2rem;
    }
    .sub-text { color: #8b949e; font-size: 1.1rem; margin-bottom: 2rem; }
    .gina-nod { color: #8b949e; font-style: italic; opacity: 0.8; }
    
    .glass-card {
        background: rgba(20, 20, 25, 0.4);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px; padding: 2rem; margin-bottom: 25px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.5);
    }
    
    .stTextArea textarea, .stTextInput input {
        background-color: rgba(10, 10, 12, 0.8) !important; color: #e6edf3 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 10px !important;
        font-size: 14px; transition: all 0.3s ease;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #4facfe !important; box-shadow: 0 0 0 2px rgba(79, 172, 254, 0.2) !important;
    }
    
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

st.markdown('<div class="gradient-text">Creator Tree</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-text">Creator search. <span class="gina-nod">Built for Gina—with a little ginger magic. ✨</span></div>', unsafe_allow_html=True)

try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 Missing Gemini API Key in Streamlit Secrets.")
    st.stop()

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

with st.expander("⚙️ Advanced Search Tuning", expanded=True):
    param_col1, param_col2, param_col3 = st.columns(3)
    with param_col1:
        profile_count = st.slider("Maximum Profiles to Target", min_value=5, max_value=150, value=20, step=5)
    with param_col2:
        selected_platforms = st.multiselect("Target Networks", options=["Instagram", "TikTok"], default=["Instagram", "TikTok"])
    with param_col3:
        follower_target = st.text_input("👥 Target Follower Range", placeholder="e.g., 10K - 50K")

st.markdown("</div>", unsafe_allow_html=True)

if "discovered_creators" not in st.session_state:
    st.session_state.discovered_creators = []
if "show_animation" not in st.session_state:
    st.session_state.show_animation = False

if st.button("🚀 Initialize Discovery Engine", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first.")
    elif not selected_platforms:
        st.warning("Please select at least one target social platform.")
    else:
        platform_str = " and ".join(selected_platforms) if len(selected_platforms) == 2 else f"exclusively {selected_platforms[0]}"
        follower_str = f" Ensure they fall in the follower range of: {follower_target}." if follower_target.strip() else ""
        
        try:
            with st.spinner(f"🌐 Aggressively traversing index to hit exact quota of {profile_count} creators..."):
                query_count = max(8, (profile_count // 5) + 3)
                
                query_generation_prompt = f"""
                Based on brand context: '{brand_context}' and campaign target: '{campaign_brief}', write exactly {query_count} highly distinct, plain-English search phrases designed to find individual, real UK-based creators on {platform_str}.{follower_str}
                Output ONLY the raw search phrases, one per line. No quotes.
                """
                query_res = client.models.generate_content(model='gemini-2.5-flash', contents=query_generation_prompt)
                search_queries = [q.strip() for q in query_res.text.split("\n") if q.strip()][:query_count]
                
                if not search_queries:
                    search_queries = [f"UK {platform_str} creators {follower_target} {campaign_brief}"]

                aggregated_search_text = ""
                raw_verified_dict = {} 
                
                for query in search_queries:
                    if len(raw_verified_dict) >= profile_count:
                        break 
                        
                    for attempt in range(3):
                        try:
                            # Search query engineered to demand structural profile metrics
                            search_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=f"Find individual {platform_str} profile web pages in the UK matching: {query}. {follower_str} CRITICAL: Provide their exact follower count, exact following count, and exact total number of posts if visible on the page.",
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
                                                # Extreme URL normalization to prevent matching errors
                                                cleaned_url = url.split('?')[0].strip(".,;:()[]{}'\"/")
                                                if cleaned_url not in raw_verified_dict:
                                                    raw_verified_dict[cleaned_url] = {"url": cleaned_url, "title": title}
                            break
                        except Exception as e:
                            if "503" in str(e) and attempt < 2:
                                time.sleep(2 ** attempt)
                                continue
                            else:
                                break

                if aggregated_search_text and len(raw_verified_dict) < profile_count:
                    found_urls = re.findall(r'(https?://[^\s()<>\"\']+)', aggregated_search_text)
                    for link in found_urls:
                        if len(raw_verified_dict) >= profile_count:
                            break
                            
                        link_lower = link.lower()
                        is_insta = "Instagram" in selected_platforms and "instagram.com" in link_lower
                        is_tiktok = "TikTok" in selected_platforms and "tiktok.com" in link_lower
                        
                        if (is_insta or is_tiktok) and not any(x in link_lower for x in ["/p/", "/tag/", "/explore/", "directory", "search", "login"]):
                            cleaned_link = link.split('?')[0].strip(".,;:()[]{}'\"/")
                            if cleaned_link not in raw_verified_dict:
                                raw_verified_dict[cleaned_link] = {"url": cleaned_link, "title": "Discovered Creator"}

            source_pool = list(raw_verified_dict.values())[:profile_count]
            
            if source_pool:
                with st.spinner(f"⚡ Synthesizing {len(source_pool)} verified data nodes (Target: {profile_count})..."):
                    clean_source_urls = [item['url'] for item in source_pool]
                    
                    format_prompt = f"""
                    You are a strict data parser. Review this exact text log:
                    ---
                    {aggregated_search_text}
                    ---
                    Extract metrics ONLY for these verified URLs: {json.dumps(clean_source_urls)}
                    
                    CRITICAL HALLUCINATION OVERRIDE RULES:
                    1. For "Followers (Est)", "Following Count", and "Total Posts": You may ONLY write a number if that exact metric is physically written in the text log.
                    2. If the text log DOES NOT explicitly state the number, you MUST output exactly "N/A (Manual Entry)". Do not guess. Do not estimate.
                    
                    Format as a JSON array of objects with keys: "Title", "Link", "Platform", "Followers (Est)", "Following Count", "Total Posts", "Snippet".
                    """
                    
                    for attempt in range(3):
                        try:
                            format_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=format_prompt,
                                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.0) 
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
                            
                            url = str(item.get("Link", item.get("link", item.get("url", "")))).split('?')[0].strip(".,;:()[]{}'\"/")
                            url_lower = url.lower()
                            
                            is_insta = "instagram.com" in url_lower
                            is_tiktok = "tiktok.com" in url_lower
                            
                            if is_insta or is_tiktok:
                                normalized_item = {
                                    "Title": str(item.get("Title", item.get("title", "@Profile"))),
                                    "Link": url,
                                    "Platform": "Instagram" if is_insta else "TikTok",
                                    "Followers (Est)": str(item.get("Followers (Est)", "N/A (Manual Entry)")),
                                    "Following Count": str(item.get("Following Count", "N/A (Manual Entry)")),
                                    "Total Posts": str(item.get("Total Posts", "N/A (Manual Entry)")),
                                    "Snippet": str(item.get("Snippet", "Verified entity."))
                                }
                                normalized_list.append(normalized_item)
                    
                    if normalized_list:
                        df_results = pd.DataFrame(normalized_list).drop_duplicates(subset=["Link"]).head(profile_count)
                        st.session_state.discovered_creators = df_results.to_dict('records')
                        
                        st.session_state.show_animation = True
                        
                        if len(df_results) < profile_count:
                            st.toast(f'Found {len(df_results)} profiles. Maxed out niche footprint!', icon='⚠️')
                        else:
                            st.toast(f'Quota hit! Loaded exactly {len(df_results)} profiles.', icon='✅')
                    else:
                        st.warning("Data footprints located, but clean entity routing failed. Adjust parameters.")
            else:
                st.warning("No direct live profile links captured. Broaden campaign terms.")
                
        except Exception as e:
            st.error(f"Engine sequence interrupted. Error: {str(e)}")

if st.session_state.show_animation:
    st.markdown("""
        <style>
        @keyframes flyPan {
            0% { transform: translate(-10vw, 30vh) scale(1) rotate(0deg); opacity: 1; }
            20% { transform: translate(25vw, 15vh) scale(1.3) rotate(-10deg); }
            40% { transform: translate(50vw, 35vh) scale(1.6) rotate(10deg); }
            60% { transform: translate(75vw, 10vh) scale(1.3) rotate(-15deg); }
            80% { transform: translate(90vw, 20vh) scale(1) rotate(5deg); opacity: 0.8; }
            100% { transform: translate(110vw, -10vh) scale(0.8) rotate(0deg); opacity: 0; }
        }
        .pan-fairy {
            position: fixed;
            top: 30%;
            left: 0;
            font-size: 80px;
            pointer-events: none;
            animation: flyPan 3.5s cubic-bezier(0.25, 0.1, 0.25, 1) forwards;
            z-index: 99999;
            filter: drop-shadow(0px 0px 15px rgba(255,215,0,0.8));
        }
        </style>
        <div class="pan-fairy">🧚‍♂️✨☁️</div>
    """, unsafe_allow_html=True)
    st.session_state.show_animation = False 

if st.session_state.discovered_creators:
    st.write("---")
    st.markdown("### 📊 Creator Report")
    
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    cols = ["Title", "Link", "Platform", "Followers (Est)", "Following Count", "Total Posts", "Snippet"]
    df_display = df_display.reindex(columns=[c for c in cols if c in df_display.columns])

    edited_df = st.data_editor(
        df_display,
        column_config={
            "Link": st.column_config.LinkColumn("Profile URL"),
            "Followers (Est)": st.column_config.TextColumn("Followers (Est)"),
            "Following Count": st.column_config.TextColumn("Following Count (BS Detector)"),
            "Total Posts": st.column_config.TextColumn("Total Posts (Dedication Check)"),
        },
        disabled=["Title", "Link", "Platform", "Snippet"],
        hide_index=True,
        width="stretch"
    )
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Creator Report (CSV)",
        data=csv,
        file_name="creator_report.csv",
        mime="text/csv",
    )
