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
        with st.spinner("🧠 AI is executing live Google Search grounding to find authentic profiles..."):
            try:
                # Using explicit proto mappings to prevent library dictionary parsing conflicts
                model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    tools=[genai.protos.Tool(google_search=genai.protos.Tool.GoogleSearch())]
                )
                
                prompt = f"""
                You are an advanced influencer marketing research tool.
                Analyze this campaign brief: '{campaign_brief}'.
                
                Use live Google Search data to find up to 8 REAL, active, prominent creators on Instagram or TikTok matching this exact target audience and geographic region.
                Do not guess or invent usernames. Every profile must correspond to an actual, live social media account indexed on the web.
                
                Output the results ONLY as a valid JSON array of objects. Do not include markdown code block styling (like ```json). Start directly with the opening bracket [.
                
                Each object in the array must have exactly these keys:
                "Title", "Link", "Platform", "Followers (Est)", "Engagement Rate", "Snippet"
                
                Guidelines:
                - Title: The creator's name or main social handle (e.g., "@tech_tom").
                - Link: A valid link to their real profile (e.g., "[https://www.instagram.com/tech_tom](https://www.instagram.com/tech_tom)").
                - Platform: Must be exactly 'Instagram' or 'TikTok'.
                - Followers (Est): Their approximate current follower size based on search snippets.
                - Engagement Rate: A realistic estimate percentage or range based on active performance data.
                - Snippet: A short explanation of why they match this specific brief.
                """
                
                response = model.generate_content(prompt)
                raw_data = response.text.strip()
                
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
                    df_results = pd.DataFrame(creators_list)
                    
                    if not df_results.empty and "Link" in df_results.columns:
                        st.session_state.discovered_creators = df_results.to_dict('records')
                        st.success(f"🎉 Successfully generated {len(df_results)} creator profile matches!")
                    else:
                        st.warning("The system generated an empty dataset. Try providing more details in your brief.")
                else:
                    st.warning("No data returned from the workspace engine.")
                    
            except Exception as e:
                st.error(f"An error occurred during discovery: {str(e)}")

# 4. Phase 2: Display and Export Data
if st.session_state.discovered_creators:
    st.write("---")
    st.subheader("📋 Discovered Profiles & Data Hub")
    st.info("💡 Tip: You can double-click directly inside the 'Followers (Est)' and 'Engagement Rate' cells to refine or update them manually before downloading!")
    
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
