import streamlit as st
import openai
from langchain.agents import initialize_agent, Tool, AgentType
from langchain.llms import OpenAI
import pandas as pd
import sqlite3
import requests
from bs4 import BeautifulSoup

# Helper function to get table columns
def get_table_columns(connection):
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(data_table);")
    columns_info = cursor.fetchall()
    columns = [info[1] for info in columns_info]  # Column names are in the second position
    return columns

# Function to load CSV into SQLite
def load_csv_to_sqlite(file):
    df = pd.read_csv(file)
    conn = sqlite3.connect(':memory:')
    df.to_sql('data_table', conn, index=False, if_exists='replace')
    return conn, df

# Function to create tools with access to conn and df
def create_tools(conn, df):
    columns = get_table_columns(conn)

    def text_to_sql(query):
        prompt = f"""
        You are an expert SQL developer. Convert the following natural language query into a valid SQL query that can be executed against the provided SQLite database schema.

        Schema:
        - Table name: data_table
        - Columns: {', '.join(columns)}

        Query: {query}

        SQL Query:
        """
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0
        )
        sql_query = response.choices[0].text.strip()
        return sql_query

    def preprocess_sql(sql_query):
        prompt = f"""
        You are an SQL expert. Analyze the following SQL query for correctness based on the provided schema and make necessary corrections or optimizations.

        Schema:
        - Table name: data_table
        - Columns: {', '.join(columns)}

        SQL Query:
        {sql_query}

        Corrected/Optimized SQL Query:
        """
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            temperature=0
        )
        corrected_query = response.choices[0].text.strip()
        return corrected_query

    def execute_sql(sql_query):
        try:
            result_df = pd.read_sql_query(sql_query, conn)
            return result_df.to_string()
        except Exception as e:
            return f"Error executing SQL query: {e}"

    def scrape_yahoo_finance(stock_symbol):
        url = f"https://finance.yahoo.com/quote/{stock_symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        try:
            price = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'}).text
            change = soup.find('fin-streamer', {'data-field': 'regularMarketChange'}).text
            percent_change = soup.find('fin-streamer', {'data-field': 'regularMarketChangePercent'}).text
            return f"Stock: {stock_symbol}\nPrice: {price}\nChange: {change} ({percent_change})"
        except AttributeError:
            return f"Could not retrieve data for {stock_symbol}."

    def generate_summary_report(dataframe, questions):
        summary = ""
        for q in questions:
            prompt = f"""
            You are an analytical assistant. Based on the following data, provide a concise answer to the question.

            Data:
            {dataframe.to_csv(index=False)}

            Question: {q}

            Answer:
            """
            response = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=200,
                temperature=0.5
            )
            answer = response.choices[0].text.strip()
            summary += f"**{q}**\n{answer}\n\n"
        return summary

    def load_csv_tool(file):
        conn_new, df_new = load_csv_to_sqlite(file)
        return "CSV file loaded successfully into the in-memory SQLite database."

    # Define the tools
    tools = [
        Tool(
            name="Text-to-SQL",
            func=text_to_sql,
            description="Converts natural language queries into SQL queries."
        ),
        Tool(
            name="Web-Scraping",
            func=scrape_yahoo_finance,
            description="Scrapes the latest stock prices from Yahoo Finance. Input should be the stock symbol."
        ),
        Tool(
            name="Generate Summary",
            func=lambda questions: generate_summary_report(df, questions),
            description="Generates a summary report based on multiple questions about the data."
        ),
        Tool(
            name="Load CSV",
            func=lambda file: load_csv_tool(file),
            description="Loads a CSV file into an in-memory SQLite database. Input should be the uploaded CSV file."
        ),
        Tool(
            name="Preprocess SQL",
            func=preprocess_sql,
            description="Formats and validates SQL queries based on the database schema."
        ),
        Tool(
            name="Execute SQL",
            func=execute_sql,
            description="Executes a SQL query against the in-memory SQLite database and returns the results."
        )
    ]

    return tools

# Initialize Streamlit app
st.title("📝 Advanced SQL Q&A with GPT-4 and LangChain")

# Sidebar for API keys
with st.sidebar:
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    if openai_api_key:
        openai.api_key = openai_api_key

# File uploader
uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])

# User question input
question = st.text_input("Ask something about the file", placeholder="e.g., Show me the top 5 companies by market cap")

# Placeholder for response
response_placeholder = st.empty()

# Handle user query
if uploaded_file and question and openai_api_key:
    try:
        # Load CSV into SQLite
        conn, df = load_csv_to_sqlite(uploaded_file)
        
        # Create tools with access to conn and df
        tools = create_tools(conn, df)
        
        # Initialize the LLM
        llm = OpenAI(temperature=0.0, openai_api_key=openai_api_key, model="gpt-4")
        
        # Initialize the agent with tools
        agent = initialize_agent(
            tools=tools,
            llm=llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True
        )
        
        # Run the agent with the user's question
        with st.spinner("Processing your query..."):
            response = agent.run(question)
        
        # Display the response
        response_placeholder.text_area("### Response", value=response, height=300)
        
    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    if not openai_api_key and uploaded_file and question:
        st.info("Please provide your OpenAI API key to proceed.")
