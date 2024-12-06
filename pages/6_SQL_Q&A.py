import streamlit as st
import anthropic
import pandas as pd
import sqlite3
import requests

with st.sidebar:
    anthropic_api_key = st.text_input(
        "Anthropic API Key", key="file_qa_api_key", type="password")
    "[View the source code](https://github.com/streamlit/llm-examples/blob/main/pages/1_File_Q%26A.py)"
    "[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/streamlit/llm-examples?quickstart=1)"

st.title("📝 File Q&A with Anthropic")
uploaded_file = st.file_uploader(
    "Upload an article", type=("txt", "md", "csv"))
question = st.text_input(
    "Ask something about the article",
    placeholder="Can you give me a short summary?",
    disabled=not uploaded_file,
)

if uploaded_file and question and not anthropic_api_key:
    st.info("Please add your Anthropic API key to continue.")

if uploaded_file and question and anthropic_api_key:
    # Check the file type and read accordingly
    if uploaded_file.name.endswith(".csv"):
        # Read the CSV file into a pandas DataFrame
        df = pd.read_csv(uploaded_file)

        # Create an in-memory SQLite database
        conn = sqlite3.connect(':memory:')
        df.to_sql('data_table', conn, index=False, if_exists='replace')

        # Prepare the prompt for generating SQL query
        prompt = f"\n\nHuman: Generate a SQL query for the following question: {question}\n\nAssistant:"

        client = anthropic.Client(api_key=anthropic_api_key)
        try:
            # Generate SQL query using the LLM
            response = client.completions.create(
                prompt=prompt,
                stop_sequences=[anthropic.HUMAN_PROMPT],
                model="claude-2",  # "claude-3-opus" for Claude 3 model
                max_tokens_to_sample=100,
            )
            sql_query = response.completion.strip()
            st.write("### Generated SQL Query")
            st.write(sql_query)

            # Execute the generated SQL query
            result_df = pd.read_sql_query(sql_query, conn)
            st.write("### Query Results")
            st.dataframe(result_df)

        except Exception as e:
            st.error(f"Error during API call or SQL execution: {e}")
            st.write("Prompt sent:", prompt)

    else:
        # Read text or markdown file
        article = uploaded_file.read().decode()
        prompt = f"""\n\nHuman: Here's an article:\n\n<article>
        {article}\n\n</article>\n\n{question}\n\nAssistant:"""

        client = anthropic.Client(api_key=anthropic_api_key)
        try:
            response = client.completions.create(
                prompt=prompt,
                stop_sequences=[anthropic.HUMAN_PROMPT],
                model="claude-2",  # "claude-2" for Claude 2 model
                max_tokens_to_sample=100,
            )
            st.write("### Answer")
            st.write(response.completion)
        except Exception as e:
            st.error(f"Error during API call: {e}")
            st.write("Prompt sent:", prompt)
