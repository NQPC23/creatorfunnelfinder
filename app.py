import streamlit as st
import google.generativeai as genai
from duckduckgo_search import DDGS
import pandas as pd

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
        with st.spinner("🧠 AI is analyzing your brief and scanning platforms..."):
            try:
                # Use AI to generate hyper-focused search queries based on the brief
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = f"""
                Analyze this influencer marketing campaign brief: '{campaign_brief}'.
                Generate 3 distinct, highly targeted keyword search combinations wrapped in quotes to find matching creators on Instagram or TikTok via Google search indexing.
                Output ONLY the search queries, one per line. Do not include numbers or bullet points.
                """
                
                response = model.generate_content(prompt)
                queries = [q.strip() for q in response.text.strip().split("\n") if q.strip()]
                
                # Run the X-ray searches via DuckDuckGo
                all_results = []
                with DDGS() as ddgs:
                    for query in queries[:3]:
                        clean_query = query.replace('"', '').replace("'", "")
                        results = ddgs.text(clean_query, max_results=5)
                        if results:
                            for r in results:
                                all_results.append({
                                    "Title": r.get("title", "N/A"),
                                    "Link": r.get("href", "N/A"),
                                    "Snippet": r.get("body", "N/A")
                                })
                
                if all_results:
                    # Convert to clean dataframe and remove duplicate profile links
                    df_results = pd.DataFrame(all_results).drop_duplicates(subset=["Link"])
                    df_results["Platform"] = df_results["Link"].apply(
                        lambda x: "Instagram" if "instagram.com" in str(x).lower() 
                        else ("TikTok" if "tiktok.com" in str(x).lower() else "Social Media")
                    )
                    
                    # Store in session state for tracking
                    st.session_state.discovered_creators = df_results.to_dict('records')
                    st.success(f"🎉 Found {len(df_results)} potential creator profiles!")
                else:
                    st.warning("No search results returned. Try broadening your campaign brief description.")
                    
            except Exception as e:
                st.error(f"An error occurred during discovery: {str(e)}")

# 4. Phase 2: Display and Export Data
if st.session_state.discovered_creators:
    st.write("---")
    st.subheader("📋 Discovered Profiles & Data Hub")
    
    df_display = pd.DataFrame(st.session_state.discovered_creators)
    
    # Interactive data dashboard layout
    edited_df = st.data_editor(
        df_display,
        column_config={
            "Link": st.column_config.LinkColumn("Profile URL"),
        },
        disabled=["Title", "Link", "Snippet", "Platform"],
        hide_index=True,
        use_container_width=True
    )
    
    # CSV Data Downloader
    csv = edited_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Selected Creators to CSV",
        data=csv,
        file_name="discovered_creators.csv",
        mime="text/csv",
    )
