import streamlit as st
import pandas as pd
import openai

st.set_page_config(page_title="Feedback to Backlog Generator", layout="wide")

st.title("📝 Consumer Feedback to Product Backlog Generator")

st.markdown(
    """
    This app lets you upload a CSV or Excel file with consumer feedback and generates a backlog with product enhancements (EPICs & user stories).

    **Instructions:**
    - Your file should have columns for feedback, episode, and market.
    - The app will analyze feedback, surface top pain points and opportunities by episode (highlighting the markets in which they appear), and suggest EPICs and user stories.
    - User stories will follow the format: "As a [role], I want [an action] so that [a benefit]".
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

    if st.button("Analyze Feedback", disabled=not groq_api_key):
        with st.spinner("Analyzing feedback by episode and highlighting markets..."):
            episode_results = []
            grouped = df.dropna(subset=[feedback_col, episode_col, market_col]).groupby(episode_col)

            for episode, group in grouped:
                # For each episode, map markets to their feedback
                market_feedback = group.groupby(market_col)[feedback_col].apply(lambda x: x.dropna().astype(str).tolist()).to_dict()

                # Combine all feedback for this episode
                all_feedback = []
                for feedbacks in market_feedback.values():
                    all_feedback.extend(feedbacks)
                feedback_sample = "\n".join(all_feedback[:200])

                # Construct prompt to extract pain points and opportunities, highlighting the markets
                prompt_insights = (
                    "You are a product manager. Analyze the following consumer feedback for Episode '{}'. "
                    "Identify the top 5 pain points and top 5 opportunities for improvement. For each, specify the markets in which they have been flagged. "
                    "Provide your answer in this format:\n"
                    "Pain Point/Opportunity: <description> | Markets: <comma-separated markets>\n"
                    "Repeat for all pain points and opportunities.\n\n"
                    "Feedback grouped by market:\n".format(episode)
                )
                for market, feedbacks in market_feedback.items():
                    prompt_insights += f"--- {market} ---\n"
                    prompt_insights += "\n".join(feedbacks[:30]) + "\n"

                try:
                    response = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[
                            {"role": "system", "content": "You are a helpful product manager."},
                            {"role": "user", "content": prompt_insights},
                        ],
                        max_tokens=700,
                    )
                    insights = response.choices[0].message.content
                except Exception as e:
                    insights = f"Groq API error: {e}"

                # Now create backlog (EPICs and user stories, user stories in required format)
                prompt_backlog = (
                    f"Based on the following consumer feedback for Episode '{episode}', generate a backlog of product enhancements. "
                    "Format as:\n- EPIC: <epic name>\n  - User Story 1: As a [role], I want [an action] so that [a benefit].\n  - User Story 2: ...\n"
                    "Base the EPICs and user stories on the pain points and opportunities you've identified. "
                    "Ensure all user stories follow the format 'As a [role], I want [an action] so that [a benefit]'.\n\n"
                    "Feedback grouped by market:\n"
                )
                for market, feedbacks in market_feedback.items():
                    prompt_backlog += f"--- {market} ---\n"
                    prompt_backlog += "\n".join(feedbacks[:30]) + "\n"

                try:
                    response2 = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[
                            {"role": "system", "content": "You are a helpful product manager."},
                            {"role": "user", "content": prompt_backlog},
                        ],
                        max_tokens=900,
                    )
                    backlog = response2.choices[0].message.content
                except Exception as e:
                    backlog = f"Groq API error: {e}"

                episode_results.append({
                    "episode": episode,
                    "insights": insights,
                    "backlog": backlog,
                })

            # Render results
            st.subheader("Pain Points & Opportunities by Episode (with markets highlighted)")
            for result in episode_results:
                with st.expander(f"Episode: {result['episode']}"):
                    st.markdown("**Top Pain Points & Opportunities (with markets):**")
                    st.markdown(result["insights"])
                    st.markdown("**Generated Backlog (EPICs & User Stories):**")
                    st.code(result["backlog"], language="markdown")

        st.success("Done! Explore the analysis and backlog by expanding each episode above.")
    elif not groq_api_key:
        st.info("Please enter your Groq API key in the sidebar to enable analysis.")

else:
    st.info("Upload a CSV or Excel file to get started.")
