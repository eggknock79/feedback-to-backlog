import streamlit as st
import pandas as pd
import openai

st.set_page_config(page_title="Feedback to Backlog Generator", layout="wide")

st.title("📝 Consumer Feedback to Product Backlog Generator")

st.markdown(
    """
    This app lets you upload a CSV or Excel file with consumer feedback and generates a backlog with product enhancements (EPICs & user stories).

    **Instructions:**
    - Your file should have columns for feedback, episode, market, and country.
    - The app will analyze feedback, surface key pain points and opportunities, and suggest EPICs and user stories.
    - Enter your [Groq API key](https://console.groq.com/).
    """
)

groq_api_key = st.sidebar.text_input(
    "Enter your Groq API key", type="password", help="Get one at https://console.groq.com/"
)

client = None
if groq_api_key:
    client = openai.OpenAI(
        api_key=groq_api_key,
        base_url="https://api.groq.com/openai/v1"
    )

uploaded_file = st.file_uploader(
    "Upload your feedback CSV or Excel file", type=["csv", "xlsx"]
)

if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    st.subheader("Step 1: Select Columns")
    object_cols = [col for col in df.columns if df[col].dtype == "O"]

    feedback_col = st.selectbox("Select the column containing feedback text", object_cols, key="feedback_col")
    episode_col = st.selectbox("Select the column for episode", object_cols, key="episode_col")
    market_col = st.selectbox("Select the column for market", object_cols, key="market_col")
    country_col = st.selectbox("Select the column for country", object_cols, key="country_col")

    if st.button("Analyze Feedback", disabled=not groq_api_key):
        with st.spinner("Analyzing feedback by episode, market, and country..."):
            results = []
            grouped = df.dropna(subset=[feedback_col, episode_col, market_col, country_col]).groupby(
                [episode_col, market_col, country_col]
            )
            for (episode, market, country), group in grouped:
                feedback_texts = group[feedback_col].dropna().astype(str).tolist()
                if not feedback_texts:
                    continue
                feedback_sample = "\n".join(feedback_texts[:200])

                prompt_insights = (
                    "You are a product manager. Analyze this list of consumer feedback. "
                    "Identify the top 5 pain points and top 5 opportunities for improvement. "
                    "List each pain point/opportunity with a short summary.\n\n"
                    f"Feedback:\n{feedback_sample}\n"
                )

                try:
                    response = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[
                            {"role": "system", "content": "You are a helpful product manager."},
                            {"role": "user", "content": prompt_insights},
                        ],
                        max_tokens=500,
                    )
                    insights = response.choices[0].message.content
                except Exception as e:
                    insights = f"Groq API error: {e}"

                results.append({
                    "episode": episode,
                    "market": market,
                    "country": country,
                    "insights": insights,
                })

            # Render results
            st.subheader("Analysis of Pain Points & Opportunities by Episode, Market, and Country")
            for result in results:
                with st.expander(f"Episode: {result['episode']} | Market: {result['market']} | Country: {result['country']}"):
                    st.markdown(result["insights"])

        st.success("Done! Explore the analysis by expanding each section above.")
    elif not groq_api_key:
        st.info("Please enter your Groq API key in the sidebar to enable analysis.")

else:
    st.info("Upload a CSV or Excel file to get started.")
