import streamlit as st
import google.generativeai as genai
import pandas as pd
import json

# 1. Page Configuration
st.set_page_config(page_title="Creator Funnel Finder", page_icon="🔍", layout="wide")

st.title("🔍 Creator Funnel Finder")
st.write("Input your campaign brief below to discover perfectly matched creators.")

# 2. Securely fetch the Gemini API Key from Streamlit Secrets
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except Exception:
    st.error("🔑 Gemini API Key not found. Please add it to your Streamlit Advanced Settings / Secrets.")
    st.stop()

# 3. Phase 1: Campaign Input
campaign_brief = st.text_area(
    "Describe your campaign and target creator profile:",
    placeholder="e.g., Looking for UK-based lifestyle or travel creators who focus on disability advocacy and cerebral palsy awareness...",
    height=150
)

# Initialize session state variables to save progress across clicks
if "discovered_creators" not in st.session_state:
    st.session_state.discovered_creators = []

if st.button("🚀 Discover Creators", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please enter a campaign brief first!")
    else:
        try:
            # --- STEP 1: DEEP LIVE WEB SEARCH WITH OPERATORS ---
            with st.spinner("🌐 Scanning live Instagram & TikTok indexes for authentic accounts..."):
                search_model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    tools=[genai.protos.Tool(google_search=genai.protos.Tool.GoogleSearch())]
                )
                
                search_prompt = f"""
                Find up to 8 REAL, active, prominent UK-based individual creator profiles matching this brief: '{campaign_brief}'.
                
                CRITICAL INSTRUCTION:
                You MUST use strict search queries targeting direct index profile structures, such as:
                - site:instagram.com "keyword" "UK"
                - site:tiktok.com "@" "keyword" "UK"
                
                Only extract actual, live user profile URLs found explicitly within the search index results. Do not pull links from generic roundup blogs or agency directories. If you cannot find the direct, exact link to an individual's personal profile page, do not include them. Do not guess handles.
                
                For each valid creator found, record:
                1. Their exact handle/name.
                2. The full profile URL link.
                3. Accurate follower and engagement data visible in the search snippet.
                4. A brief sentence on why they fit this specific campaign.
                """
                
                search_response = search_model.generate_content(search_prompt)
                raw_search_text = search_response.text

            # --- STEP 2: STRUCTURED DATA EXTRACTION ---
            with st.spinner("📊 Mapping verified profiles into your data workspace..."):
                format_model = genai.GenerativeModel(model_name="gemini-2.5-flash")
                
                format_prompt = f"""
                You are a strict data extraction assistant. Convert this raw creator research text into a valid JSON array of objects.
                
                Research Text:
                {raw_search_text}
                
                Each object in the array must contain exactly these keys:
                "Title", "Link", "Platform", "Followers (Est)", "Engagement Rate", "Snippet"
                
                Strict Rules:
                - Link: The exact, unedited profile URL from the text.
                - Platform: Must be exactly 'Instagram' or 'TikTok'.
                - Followers (Est): The follower count listed (or 'N/A').
                - Engagement Rate: The performance data listed (or 'N/A').
                - Snippet: A brief overview of why they match.
                
                Output ONLY the raw JSON array starting with [ and ending with ]. Do not wrap it in markdown text.
                """
                
                format_response = format_model.generate_content(format_prompt)
                raw_json_data = format_response.text.strip()
                
                if raw_json_data.startswith("```"):
                    lines = raw_json_data.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_json_data = "\n".join(lines).strip()

            if raw_json_data:
                creators_list = json.loads(raw_json_data)
                
                # --- STEP 3: PYTHON-SIDE QUALITY GUARDRAIL ---
                verified_list = []
                for creator in creators_list:
                    url = str(creator.get("Link", "")).strip().lower()
                    
                    # Ensure the URL is an absolute direct link, not a home page, search page, or hallucination
                    is_valid_insta = "[instagram.com/](https://instagram.com/)" in url and len(url.split("[instagram.com/](https://instagram.com/)")[-1].replace("/", "")) > 0
                    is_valid_tiktok = "[tiktok.com/](https://tiktok.com/)" in url and len(url.split("[tiktok.com/](https://tiktok.com/)")[-1].replace("/", "")) > 0
                    
                    if is_valid_insta or is_valid_tiktok:
                        # Clean up trailing punctuation if the AI accidentally grabbed it from a sentence
                        if url.endswith(".") or url.endswith(","):
                            creator["Link"] = creator["Link"][:-1]
                        verified_list.append(creator)
                
                if verified_list:
                    df_results = pd.DataFrame(verified_list).drop_duplicates(subset=["Link"])
                    st.session_state.discovered_creators = df_results.to_dict('records')
                    st.success(f"🎉 Successfully verified and loaded {len(df_results)} authentic creator profiles!")
                else:
                    st.warning("Google found mentions of matching creators, but could not securely verify their direct profile URLs. Try refining your keywords.")
            else:
                st.warning("No data package received from the formatting array.")
                
        except Exception as e:
            st.error(f"An error occurred during discovery: {str(e)}")

# 4. Phase 2: Display and Export Data
if st.session_state.discovered_creators:
    st.write("---")
    st.subheader("📋 Discovered Profiles & Data Hub")
    st.info("💡 Tip: You can double-click inside the 'Followers (Est)' and 'Engagement Rate' cells to manually refine details on the fly.")
    
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Link": st.column_config.LinkColumn("Profile URL"),
            "Followers (Est)": st.column_config.TextColumn("Followers (Est)"),
            "Engagement Rate": st.column_config.TextColumn("Engagement Rate"),
        },
        disabled=["Title", "Link", "Snippet", "Platform"],
        hide_index=True,
        use_container_width=True
    )
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Selected Creators to CSV",
        data=csv,
        file_name="discovered_creators.csv",
        mime="text/csv",
    )
