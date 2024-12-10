import streamlit as st
import openai
import pandas as pd
import sqlite3

print(openai.__version__)

st.title("📝 SQL Q&A with GPT-4")

with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    if openai_api_key:
        openai.api_key = openai_api_key

uploaded_file = st.file_uploader("Upload an article or CSV", type=("txt", "md", "csv"))
question = st.text_input("Ask something about the file",
                         placeholder="Can you give me a short summary?")

if uploaded_file and question and openai_api_key:
    if uploaded_file.name.endswith(".csv"):
        # CSV scenario: We'll try to generate and execute a SQL query
        df = pd.read_csv(uploaded_file)
        conn = sqlite3.connect(':memory:')
        df.to_sql('data_table', conn, index=False, if_exists='replace')

        # Create a system and user message prompt to get the SQL query
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant skilled at generating SQL queries. "
                           "You have access to a table called 'data_table' derived from a CSV file."
            },
            {
                "role": "user",
                "content": f"Generate a SQL query for the following question: {question}"
            }
        ]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=200,
                temperature=0  # Adjust temperature as needed
            )
            raw_response = response.choices[0].message.content.strip()
            lines = raw_response.split('\n')
            # Extract lines that look like SQL
            sql_lines = [
                line for line in lines if 'SELECT' in line.upper() or 'FROM' in line.upper() 
                or 'WHERE' in line.upper() or 'ORDER BY' in line.upper() or 'GROUP BY' in line.upper()
            ]
            clean_query = ' '.join(sql_lines).strip()
            # Ensure ending semicolon
            if not clean_query.endswith(';'):
                clean_query += ';'

            try:
                result_df = pd.read_sql_query(clean_query, conn)
                st.write("### Query Results")
                st.dataframe(result_df)
                st.write(f"DataFrame has {result_df.shape[0]} rows and {result_df.shape[1]} columns.")
            except Exception as e:
                st.error(f"Error executing SQL query: {e}")
                st.write("Attempted Query:", clean_query)

        except Exception as e:
            st.error(f"Error during API call: {e}")

    else:
        # Text/Markdown scenario
        article = uploaded_file.read().decode()
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that can answer questions about given text."
            },
            {
                "role": "user",
                "content": f"Here's an article:\n{article}\n{question}"
            }
        ]

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=messages,
                max_tokens=300,
                temperature=0
            )
            answer = response.choices[0].message.content.strip()
            st.write("### Answer")
            st.write(answer)
        except Exception as e:
            st.error(f"Error during API call: {e}")
            st.write("Messages:", messages)

else:
    if not openai_api_key and uploaded_file and question:
        st.info("Please provide your OpenAI API key to proceed.")
