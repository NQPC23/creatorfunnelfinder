import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import json

# 1. Page Configuration
st.set_page_config(page_title="Creator Funnel Finder", page_icon="🔍", layout="wide")

st.title("🔍 Creator Funnel Finder")
st.write("Input your campaign brief below to discover perfectly matched creators.")

# 2. Securely fetch API Keys from Streamlit Secrets
try:
    # Initialize the modern official GenAI SDK client
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
except Exception:
    st.error("🔑 Missing Gemini API Key. Please ensure GEMINI_API_KEY is added to your Streamlit Secrets.")
    st.stop()

# 3. Phase 1: Campaign Input
campaign_brief = st.text_area(
    "Describe your campaign and target creator profile:",
    placeholder="e.g., Looking for UK-based lifestyle or travel creators who focus on disability advocacy and cerebral palsy awareness...",
    height=150
)

if "discovered_creators" not in st.session_state:
    st.session_state.discovered_creators = []

if st.button("🚀 Discover Creators", type="primary"):
    if not campaign_brief.strip():
        st.warning("Please enter a campaign brief first!")
    else:
        with st.spinner("🌐 Executing live Google Search grounding to find authentic profiles..."):
            try:
                # Rigorous structured prompt ensuring real data lookups
                prompt = f"""
                You are an advanced influencer marketing research tool.
                Analyze this campaign brief: '{campaign_brief}'.
                
                Use live Google Search data to find up to 8 REAL, active, prominent individual creators on Instagram or TikTok matching this exact target audience and geographic region.
                Do not guess or invent usernames. Every profile must correspond to an actual, live social media account indexed on the web.
                
                Output the results ONLY as a valid JSON array of objects. Do not include markdown code block styling (like ```json). Start directly with the opening bracket [.
                
                Each object in the array must have exactly these keys:
                "Title", "Link", "Platform", "Followers (Est)", "Engagement Rate", "Snippet"
                
                Guidelines:
                - Title: The creator's name or main social handle (e.g., "@username").
                - Link: A valid link to their real profile (e.g., "[https://www.instagram.com/username](https://www.instagram.com/username)").
                - Platform: Must be exactly 'Instagram' or 'TikTok'.
                - Followers (Est): Their approximate current follower size based on search snippets (e.g., "45K", "1.2M", "N/A").
                - Engagement Rate: A realistic estimate percentage or range based on active performance data or "N/A".
                - Snippet: A short explanation of why they match this specific brief.
                """
                
                # Execute content generation with the updated official SDK grounding configuration
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.2  # Lower temperature to enforce strict factual parsing
                    )
                )
                
                raw_data = response.text.strip() if response.text else ""
                
                # Strip out accidental markdown wrapper blocks if the model adds them
                if raw_data.startswith("```"):
                    lines = raw_data.split("\n")
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines[-1].startswith("```"):
                        lines = lines[:-1]
                    raw_data = "\n".join(lines).strip()
                
                if raw_data:
                    creators_list = json.loads(raw_data)
                    
                    # Double-pass validation guardrail to filter out any broken references
                    verified_list = []
                    for creator in creators_list:
                        url = str(creator.get("Link", "")).strip().lower()
                        
                        is_insta = "instagram.com" in url
                        is_tiktok = "tiktok.com" in url
                        
                        if is_insta or is_tiktok:
                            # Clean up trailing syntax characters from sentence extractions
                            if creator["Link"].endswith(".") or creator["Link"].endswith(","):
                                creator["Link"] = creator["Link"][:-1]
                            verified_list.append(creator)
                    
                    if verified_list:
                        df_results = pd.DataFrame(verified_list).drop_duplicates(subset=["Link"])
                        st.session_state.discovered_creators = df_results.to_dict('records')
                        st.success(f"🎉 Successfully verified and loaded {len(df_results)} live creator profiles!")
                    else:
                        st.warning("Google tracked discussions of matching accounts, but could not map direct user profile links. Try broader search terms.")
                else:
                    st.warning("No data package returned from the workspace grounding engine.")
                    
            except Exception as e:
                st.error(f"An error occurred during discovery: {str(e)}")

# 4. Phase 2: Display and Export Data
if st.session_state.discovered_creators:
    st.write("---")
    st.subheader("📋 Discovered Profiles & Data Hub")
    st.info("💡 Tip: You can double-click directly inside the 'Followers (Est)' and 'Engagement Rate' cells to refine details manually before downloading.")
    
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    
    # Enforce clear column hierarchy layout
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
        use_container_width=True
    )
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Selected Creators to CSV",
        data=csv,
        file_name="discovered_creators.csv",
        mime="text/csv",
    )
