import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json

# 1. Page Configuration
st.set_page_config(page_title="Creator Funnel Finder", page_icon="🔍", layout="wide")

st.title("🔍 Creator Funnel Finder")
st.write("Input your brand profile and campaign guidelines to discover perfectly matched creators.")

# 2. Securely fetch API Keys from Streamlit Secrets
try:
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 Missing Gemini API Key. Please ensure GEMINI_API_KEY is added to your Streamlit Secrets.")
    st.stop()

# 3. Phase 1: Context Input Hub
col1, col2 = st.columns(2)

with col1:
    brand_context = st.text_area(
        "🏷️ Brand Profile & Identity Context:",
        placeholder="e.g., An innovative B2B software tool targeting solopreneurs, focusing on efficiency, modern design, and clean aesthetics...",
        height=120
    )

with col2:
    campaign_brief = st.text_area(
        "🎯 Campaign Goal & Target Creator Vibe:",
        placeholder="e.g., Looking for UK tech creators who showcase custom workflows or step-by-step tutorials rather than generic news reviews...",
        height=120
    )

if "discovered_creators" not in st.session_state:
    st.session_state.discovered_creators = []

if st.button("🚀 Discover Matched Creators", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first!")
    else:
        try:
            # --- STAGE 1: UNCONSTRAINED LIVE SEARCH GROUNDING ---
            with st.spinner("🌐 Crawling live Google Search indexes for matching creators..."):
                search_prompt = f"""
                Perform a live Google search to locate up to 8 real, active, individual UK-based creator profiles on Instagram or TikTok who align with this setup:
                
                Brand Identity: {brand_context if brand_context.strip() else 'Generic AI/Tech Startup'}
                Campaign Strategy: {campaign_brief}
                
                Identify their handles, exact clickable links, approximate follower sizes from snippets, and why they fit. Do not make up profiles.
                """
                
                search_response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=search_prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.3
                    )
                )
                raw_search_text = search_response.text if search_response.text else ""

            # --- STAGE 2: NATIVE STRUCTURED JSON EXTRACTION ---
            if raw_search_text:
                with st.spinner("📊 Structuring verified profiles into your data workspace..."):
                    format_prompt = f"""
                    Extract the creator profile details from this raw research text into a clean JSON array of objects:
                    
                    {raw_search_text}
                    
                    Each object must follow this structure layout:
                    "Title": Name or social handle
                    "Link": Unedited profile URL page
                    "Platform": Must be exactly 'Instagram' or 'TikTok'
                    "Followers (Est)": Follower metrics noted in text or 'N/A'
                    "Engagement Rate": Estimated performance tier metric or 'N/A'
                    "Snippet": Brief rationale on why they match this specific client brief
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
                    
                    if raw_json_data:
                        raw_creators_list = json.loads(raw_json_data)
                        
                        # Case-Insensitive Normalization Guardrail
                        normalized_list = []
                        for item in raw_creators_list:
                            url = str(item.get("Link", item.get("link", item.get("url", "")))).strip()
                            url_lower = url.lower()
                            
                            if "instagram.com" in url_lower or "tiktok.com" in url_lower:
                                # Clean off trailing punctuation from text clipping
                                if url.endswith(".") or url.endswith(","):
                                    url = url[:-1]
                                    
                                normalized_item = {
                                    "Title": item.get("Title", item.get("title", item.get("handle", "@SocialProfile"))),
                                    "Link": url,
                                    "Platform": item.get("Platform", item.get("platform", "Instagram" if "instagram" in url_lower else "TikTok")),
                                    "Followers (Est)": item.get("Followers (Est)", item.get("followers", item.get("Followers", "N/A"))),
                                    "Engagement Rate": item.get("Engagement Rate", item.get("engagement", item.get("Engagement", "N/A"))),
                                    "Snippet": item.get("Snippet", item.get("snippet", item.get("description", "Live search match.")))
                                }
                                normalized_list.append(normalized_item)
                        
                        if normalized_list:
                            df_results = pd.DataFrame(normalized_list).drop_duplicates(subset=["Link"])
                            st.session_state.discovered_creators = df_results.to_dict('records')
                            st.success(f"🎉 Successfully verified and loaded {len(df_results)} creator profiles!")
                        else:
                            st.warning("Google found data for this niche, but could not isolate direct user profile links. Try using slightly broader terms.")
                    else:
                        st.error("The formatting engine encountered an extraction failure.")
            else:
                st.warning("No foundational search data was returned by the initial crawl. Try adjusting your search query words.")
                    
        except Exception as e:
            st.error(f"An error occurred during discovery: {str(e)}")

# 4. Phase 2: Interactive Data Workspace Hub
if st.session_state.discovered_creators:
    st.write("---")
    st.subheader("📋 Discovered Profiles & Data Hub")
    st.info("💡 Tip: You can double-click directly inside the 'Followers (Est)' and 'Engagement Rate' cells to manually fine-tune metrics on the fly before exporting.")
    
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
