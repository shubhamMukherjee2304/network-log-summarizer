import os

from langchain.chains.llm import LLMChain
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser

from scripts.parser import DB_FILE
from dotenv import load_dotenv

#config
load_dotenv()


try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        api_key=os.getenv("GEMINI_API_KEY")
    )
    print("Gemini LLM initialized successfully")
except Exception as e:
    print("Error initializing OpenAI. Have you set the GEMINI_API_KEY environment variable?")
    print(f"Details: {e}")
    exit()


#connecting langchain to db
db = SQLDatabase.from_uri(f"sqlite:///C:/Users/shubh/PycharmProjects/network-log-summarizer/logs/logs.db")

#sql db toolkit, provides the llm with the sql tool and information about the schema
toolkit = SQLDatabaseToolkit(db=db, llm=llm)

#sql agent executor, decides when to use the sql tool
agent_executor = create_sql_agent(
    llm = llm,
    toolkit = toolkit,
    verbose = True
)

test_query = "Fetch the timestamp, device, and messages for all logs where severity is 'FAIL'."
print(f"\n=======================================")
print(f"RUNNING TEST QUERY")
print(f"User Question: {test_query}")
print(f"=========================================")

try:
    response = agent_executor.invoke(
        {
            "input": test_query
        }
    )

    print("\n--- LLM Final Response (raw log entries)")
    print(response['output'])
    print("------------------------------------------")

except Exception as e:
    print(f"\n--- LangChain Execution Error ---")
    print(f"An error occurred during agent execution. Check your API key or connectivity.")
    print(f"Details: {e}")


SUMMARY_TEMPLATE = """
You are a highly skilled network analyst. Your task is to summarize and analyze a batch of raw network log entries.
The user provided a query, and the following raw log entries were retrieved from the database:
---
{logs}
---
Analyze these logs and provide a professional, insightful summary.

Summary Requirements:
1.  **Key Events:** Briefly describe the main incidents observed.
2.  **Anomalies:** Highlight specific anomalies such as link flaps (interface changing state multiple times), BGP neighbor drops, login failures, or duplicate IP addresses.
3.  **Affected Systems:** For each major event/anomaly, clearly state the **timeframe** (e.g., "between 10:00:05 and 10:00:10"), the **affected device/port**, and the **severity** (if possible).
4.  **Formatting:** Present the output in easy-to-read, structured bullet points or paragraphs.

DO NOT include any SQL code, database structure details, or raw log lines in your final summary.
"""

summary_prompt = PromptTemplate(input_variables=["logs"], template=SUMMARY_TEMPLATE)

#creating a summarization chain
summarization_chain = LLMChain(llm=llm, prompt=summary_prompt)

def get_log_summary(user_question):
    """
    Coordinates the entire process: SQL Query -> Data Fetch ->Summarization.

    """
    print(f"\n -- STEP 1: Running SQL agent for: '{user_question}' ---\n ")
    #passing query to sql agent for raw log entries and then call the invoke method on the executor
    raw_logs_responses = agent_executor.invoke({"input": user_question})
    raw_logs = raw_logs_responses['output']

    if not raw_logs or raw_logs.strip() == "[]":
        return "The query returned no log entries to summarize."

    print("\n -- STEP 2: Raw logs retireved generating summary.. -- \n")

    final_summary = summarization_chain.invoke({"logs":raw_logs})

    return final_summary['text']

user_input = "Retrieve all log entries from Router1, Switch A, Firewall and Router2, and then summarize the key events"

print("\n\n==============================================")
print("NETWORK LOG SUMMARIZER AGENT START")
print("==============================================")

final_summary_output = get_log_summary(user_input)

print("\n==============================================")
print("FINAL ANALYTICAL SUMMARY")
print("==============================================")
print(final_summary_output)
print("==============================================")



