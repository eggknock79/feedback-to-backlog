import streamlit as st
import pandas as pd
import openai

st.set_page_config(page_title="Feedback to Backlog Generator", layout="wide")

st.title("📝 Consumer Feedback to Product Backlog Generator")

st.markdown(
    """
    This app lets you upload a CSV or Excel file with consumer feedback and generates a backlog with product enhancements (EPICs & user stories).

    **Instructions:**
    - Your file should have a column with the feedback (e.g., "feedback", "comment", "response").
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

    st.subheader("Step 1: Select Feedback Column")
    feedback_cols = [col for col in df.columns if df[col].dtype == "O"]
    feedback_col = st.selectbox(
        "Select the column containing feedback text", feedback_cols
    )

    feedback_texts = df[feedback_col].dropna().astype(str).tolist()

    if st.button("Analyze Feedback", disabled=not groq_api_key):
        with st.spinner("Analyzing feedback, extracting pain points & opportunities..."):
            feedback_sample = "\n".join(feedback_texts[:200])

            prompt_insights = (
                "You are a product manager. Analyze this list of consumer feedback. "
                "Identify the top 5 pain points and top 5 opportunities for improvement. "
                "List each pain point/opportunity with a short summary.\n\n"
                f"Feedback:\n{feedback_sample}\n"
            )

            try:
                response = client.chat.completions.create(
                    model="llama3-70b-8192",  # Use Groq's available models (e.g. Mixtral, Llama-3, Gemma)
                    messages=[
                        {"role": "system", "content": "You are a helpful product manager."},
                        {"role": "user", "content": prompt_insights},
                    ],
                    max_tokens=500,
                )
                insights = response.choices[0].message.content
            except Exception as e:
                st.error(f"Groq API error: {e}")
                st.stop()

            st.subheader("Key Pain Points & Opportunities")
            st.markdown(insights)

            prompt_backlog = (
                "Based on the following consumer feedback, generate a backlog of product enhancements. "
                "Format as:\n- EPIC: <epic name>\n  - User Story 1: <user story>\n  - User Story 2: <user story>\n"
                "Focus on addressing pain points and leveraging opportunities.\n\n"
                f"Feedback:\n{feedback_sample}\n"
            )

            try:
                response2 = client.chat.completions.create(
                    model="llama3-70b-8192",  # Use Groq's available models
                    messages=[
                        {"role": "system", "content": "You are a helpful product manager."},
                        {"role": "user", "content": prompt_backlog},
                    ],
                    max_tokens=700,
                )
                backlog = response2.choices[0].message.content
            except Exception as e:
                st.error(f"Groq API error: {e}")
                st.stop()

            st.subheader("Generated Backlog (EPICs & User Stories)")
            st.code(backlog, language="markdown")

        st.success("Done! You can copy the backlog items above to your planning tool.")
    elif not groq_api_key:
        st.info("Please enter your Groq API key in the sidebar to enable analysis.")

else:
    st.info("Upload a CSV or Excel file to get started.")