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
        with st.spinner("🌐 Analyzing brand dynamics and crawling live Google Search indexes..."):
            try:
                # Upgraded macro prompt combining brand filters and search-snippet tracking
                prompt = f"""
                You are an enterprise influencer marketing research engine.
                
                CRITICAL TARGET INPUTS:
                - Brand Identity Context: {brand_context if brand_context.strip() else 'Generic Tech/Creative Brand'}
                - Campaign Strategy Brief: {campaign_brief}
                
                INSTRUCTIONS:
                1. Use live Google Search data to find up to 8 REAL, active, prominent individual UK-based creators on Instagram or TikTok who are an absolute perfect thematic match for BOTH the brand identity and the campaign strategy.
                2. Do not invent or guess usernames. Every profile must be an authentic, live link currently indexed on the web.
                3. Inspect the search snippets carefully to locate actual follower numbers.
                4. Estimate a highly accurate engagement rate benchmark based on their tier, content activity, and the respective platform averages.
                
                Output the results ONLY as a valid JSON array of objects. Do not include markdown code block styling (like ```json). Start directly with the opening bracket [.
                
                Columns required:
                "Title", "Link", "Platform", "Followers (Est)", "Engagement Rate", "Snippet"
                
                Guidelines:
                - Title: The handle/name (e.g., "@creative_mind").
                - Link: The direct, unedited social profile URL.
                - Platform: Must be exactly 'Instagram' or 'TikTok'.
                - Followers (Est): Exact count parsed from the google meta snippet (e.g., "42.5K", "120K").
                - Engagement Rate: A realistic percentage benchmark based on industry standards for their follower size (e.g., "4.2%", "2.1%").
                - Snippet: A clear explanation explaining exactly why this creator fits this specific Brand Context and Campaign Brief.
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.15  # Locked down low to prioritize accuracy over creative wandering
                    )
                )
                
                raw_data = response.text.strip() if response.text else ""
                
                if raw_data.startswith("```"):
                    lines = raw_data.split("\n")
                    if lines[0].startswith("```"): lines = lines[1:]
                    if lines[-1].startswith("```"): lines = lines[:-1]
                    raw_data = "\n".join(lines).strip()
                
                if raw_data:
                    creators_list = json.loads(raw_data)
                    
                    # Strict validation routing pass
                    verified_list = []
                    for creator in creators_list:
                        url = str(creator.get("Link", "")).strip().lower()
                        if "instagram.com" in url or "tiktok.com" in url:
                            if creator["Link"].endswith(".") or creator["Link"].endswith(","):
                                creator["Link"] = creator["Link"][:-1]
                            verified_list.append(creator)
                    
                    if verified_list:
                        df_results = pd.DataFrame(verified_list).drop_duplicates(subset=["Link"])
                        st.session_state.discovered_creators = df_results.to_dict('records')
                        st.success(f"🎉 Successfully verified and matched {len(df_results)} creator profiles!")
                    else:
                        st.warning("Google tracked conversations for this niche, but couldn't verify direct profile URLs. Try broadening the text strings.")
                else:
                    st.warning("No data returned from the workspace engine.")
                    
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
        use_container_width=True
    )
    
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Selected Creators to CSV",
        data=csv,
        file_name="discovered_creators.csv",
        mime="text/csv",
    )
