import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json
import time

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

# Sub-layout for parameters
param_col1, param_col2 = st.columns(2)

with param_col1:
    profile_count = st.slider(
        "📊 Number of Profiles to Discover:",
        min_value=1,
        max_value=15,
        value=5,
        help="Select the exact number of verified creator profiles you want returned in your database table."
    )

with param_col2:
    selected_platforms = st.multiselect(
        "📱 Target Social Platforms:",
        options=["Instagram", "TikTok"],
        default=["Instagram", "TikTok"],
        help="Select one or both platforms to focus your influencer discovery engine."
    )

if "discovered_creators" not in st.session_state:
    st.session_state.discovered_creators = []

if st.button("🚀 Discover Matched Creators", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please provide a campaign goal first!")
    elif not selected_platforms:
        st.warning("Please select at least one target social platform (Instagram or TikTok) before running search queries!")
    else:
        # Format selected platforms dynamically for the AI prompt string
        platform_target_string = " and ".join(selected_platforms) if len(selected_platforms) == 2 else f"exclusively {selected_platforms[0]}"
        
        try:
            # --- STAGE 1: UNCONSTRAINED LIVE SEARCH GROUNDING WITH PLATFORM QUOTA ---
            with st.spinner(f"🌐 Crawling live Google Search indexes for EXACTLY {profile_count} profiles on {platform_target_string}..."):
                search_prompt = f"""
                Perform a live Google search to locate EXACTLY {profile_count} distinct, real, active, individual UK-based creator profiles who align with this setup:
                
                Brand Identity: {brand_context if brand_context.strip() else 'Generic AI/Tech Startup'}
                Campaign Strategy: {campaign_brief}
                
                CRITICAL NETWORK LIMITATION: You must ONLY find profiles that exist on {platform_target_string}. Completely ignore any other platforms.
                
                CRITICAL QUOTA RULE: You must find and display exactly {profile_count} unique profiles. Do not return fewer than {profile_count}. Look through as many search results as necessary to fulfill this exact count. Identify their handles, exact clickable links, approximate follower sizes from snippets, and why they fit.
                """
                
                raw_search_text = ""
                for attempt in range(3):
                    try:
                        search_response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=search_prompt,
                            config=types.GenerateContentConfig(
                                tools=[types.Tool(google_search=types.GoogleSearch())],
                                temperature=0.3
                            )
                        )
                        raw_search_text = search_response.text if search_response.text else ""
                        break
                    except Exception as e:
                        if "503" in str(e) and attempt < 2:
                            time.sleep(2)
                            continue
                        else:
                            raise e

            # --- STAGE 2: NATIVE STRUCTURED JSON EXTRACTION WITH STRICT PLATFORM FILTERS ---
            if raw_search_text:
                with st.spinner(f"📊 Structuring your {profile_count} filtered profiles into the workspace..."):
                    format_prompt = f"""
                    Extract the creator profile details from this raw research text into a clean JSON array of objects.
                    
                    Research text data input:
                    {raw_search_text}
                    
                    CRITICAL EXTRACTION RULES:
                    1. The resulting JSON array MUST contain exactly {profile_count} objects matching the best discovered creators.
                    2. Only include accounts belonging to these exact networks: {selected_platforms}.
                    
                    Each object must follow this exact structural layout:
                    "Title": Name or social handle
                    "Link": Unedited profile URL page
                    "Platform": Must be exactly one of these strings: {selected_platforms}
                    "Followers (Est)": Follower metrics noted in text or 'N/A'
                    "Engagement Rate": Estimated performance tier metric or 'N/A'
                    "Snippet": Brief rationale on why they match this specific client brief
                    """
                    
                    raw_json_data = ""
                    for attempt in range(3):
                        try:
                            format_response = client.models.generate_content(
                                model='gemini-2.5-flash',
                                contents=format_prompt,
                                config=types.GenerateContentConfig(
                                    response_mime_type="application/json",
                                    temperature=0.1
                                )
                            )
                            raw_json_data = format_response.text.strip() if format_response.text else ""
                            break
                        except Exception as e:
                            if "503" in str(e) and attempt < 2:
                                time.sleep(2)
                                continue
                            else:
                                raise e
                    
                    if raw_json_data:
                        raw_creators_list = json.loads(raw_json_data)
                        
                        normalized_list = []
                        for item in raw_creators_list:
                            url = str(item.get("Link", item.get("link", item.get("url", "")))).strip()
                            url_lower = url.lower()
                            
                            # Hard validation check to see if the platform matches user multi-select choices
                            is_valid_insta = "Instagram" in selected_platforms and "instagram.com" in url_lower
                            is_valid_tiktok = "TikTok" in selected_platforms and "tiktok.com" in url_lower
                            
                            if is_valid_insta or is_valid_tiktok:
                                if url.endswith(".") or url.endswith(","):
                                    url = url[:-1]
                                    
                                normalized_item = {
                                    "Title": item.get("Title", item.get("title", item.get("handle", "@SocialProfile"))),
                                    "Link": url,
                                    "Platform": "Instagram" if is_valid_insta else "TikTok",
                                    "Followers (Est)": item.get("Followers (Est)", item.get("followers", item.get("Followers", "N/A"))),
                                    "Engagement Rate": item.get("Engagement Rate", item.get("engagement", item.get("Engagement", "N/A"))),
                                    "Snippet": item.get("Snippet", item.get("snippet", item.get("description", "Live search match.")))
                                }
                                normalized_list.append(normalized_item)
                        
                        if normalized_list:
                            # Drop identical links and safely slice array down to match user's slider configuration value
                            df_results = pd.DataFrame(normalized_list).drop_duplicates(subset=["Link"])
                            final_list = df_results.to_dict('records')[:profile_count]
                            
                            st.session_state.discovered_creators = final_list
                            st.success(f"🎉 Successfully verified and loaded exactly {len(final_list)} creator profiles!")
                        else:
                            st.warning(f"Google crawled data entries, but could not securely map verified direct links on your chosen network platform ({platform_target_string}). Try tweaking your description terms.")
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
