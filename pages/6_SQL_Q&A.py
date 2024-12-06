import streamlit as st
import anthropic
import pandas as pd
import sqlite3
from anthropic import Anthropic
print(Anthropic)
with st.sidebar:
    anthropic_api_key = st.text_input("Anthropic API Key", type="password")
    anthropic_client = Anthropic(api_key=anthropic_api_key)

st.title("📝 SQL Q&A with Anthropic")

uploaded_file = st.file_uploader(
    "Upload an article or CSV", type=("txt", "md", "csv"))
question = st.text_input("Ask something about the file",
                         placeholder="Can you give me a short summary?")

if uploaded_file and question and anthropic_api_key:
    client = anthropic.Client(api_key=anthropic_api_key)

    if uploaded_file.name.endswith(".csv"):
        # CSV scenario: We'll try to generate and execute a SQL query
        df = pd.read_csv(uploaded_file)
        conn = sqlite3.connect(':memory:')
        df.to_sql('data_table', conn, index=False, if_exists='replace')
        sql_query = """
                    SELECT name, market_cap
                    FROM data_table
                    WHERE closing_price > 50
                    ORDER BY market_cap DESC;
                    """
        prompt = f"{anthropic.HUMAN_PROMPT} You are a helpful assistant skilled at generating SQL queries.\n" \
                 f"{anthropic.HUMAN_PROMPT} Generate a SQL query for the following question: {question}{anthropic.AI_PROMPT}"
        try:

            # Use the chat endpoint
            response = anthropic_client.completions.create(
                model="claude-2",
                prompt=prompt,
                max_tokens_to_sample=100
            )
            raw_response = response.completion.strip()
            lines = raw_response.split('\n')
            sql_lines = [line for line in lines if 'SELECT' in line.upper(
            ) or 'FROM' in line.upper() or 'WHERE' in line.upper() or 'ORDER BY' in line.upper()]
            clean_query = ' '.join(sql_lines).strip()
            # Ensure you add a semicolon at the end if needed
            if not clean_query.endswith(';'):
                clean_query += ';'

            result_df = None
            try:
                result_df = pd.read_sql_query(clean_query, conn)
                st.write("### Query Results")
                st.dataframe(result_df)
            except Exception as e:
                st.error(f"Error executing SQL query: {e}")
            if result_df is not None:
                # Safe to use result_df here
                # do_something(result_df)
                st.write(
                    f"DataFrame has {result_df.shape[0]} rows and {result_df.shape[1]} columns.")
            else:
                st.write("No results to display.")
            # Execute the generated SQL query
            result_df = pd.read_sql_query(clean_query, conn)
            st.write("### Query Results")
            st.dataframe(result_df)
        except Exception as e:
            st.error(f"Error during API call or SQL execution: {e}")
            st.write("Prompt sent:", prompt)

    else:
        # Text/Markdown scenario
        article = uploaded_file.read().decode()
        prompt = f"{anthropic.HUMAN_PROMPT} Here's an article:\n{article}\n{question}{anthropic.AI_PROMPT}"

        try:
            response = client.completions.create(
                prompt=prompt,
                stop_sequences=[anthropic.HUMAN_PROMPT],
                model="claude-2",
                max_tokens_to_sample=100,
            )

            if hasattr(response, 'completion'):
                st.write("### Answer")
                st.write(response.completion)
            else:
                st.error(
                    "No completion found in the response. Check logs or prompt.")
        except Exception as e:
            st.error(f"Error during API call: {e}")
            st.write("Prompt sent:", prompt)
else:
    if not anthropic_api_key and uploaded_file and question:
        st.info("Please provide your Anthropic API key to proceed.")
