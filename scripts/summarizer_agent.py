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


class EventDetail(BaseModel):
    """A detailed summary of a single network event."""
    type: str = Field(description="Type of event, e.g., 'Interface Down/Up', 'Login Failure', 'BGP Drop', 'Critical Error'.")
    device: str = Field(description="Name of the affected device, e.g., 'Router1', 'SwitchA'.")
    port: str = Field(description="Affected interface or service, e.g., 'Gig0/1', 'Vlan1', 'ssh'. Use 'N/A' if not applicable.")
    severity: str = Field(description="Severity level, e.g., 'CRIT', 'ERROR', 'WARN', 'INFO'.")
    count: int = Field(description="Number of times this specific event (or type of event) occurred in the logs.")

class NetworkSummary(BaseModel):
    """The complete structured summary for the network log analysis."""
    timeframe: str = Field(description="The start and end time range covered by the analyzed logs, e.g., 'Sep 30 10:00:05 - 12:01:00'.")
    summary_text: str = Field(description="A detailed, plain English summary of the analysis, providing insights and context.")
    events: list[EventDetail] = Field(description="A list of structured, key network events identified in the logs.")


parser = JsonOutputParser(pydantic_object=NetworkSummary)
parser_instructions = parser.get_format_instructions()

SUMMARY_TEMPLATE = """
You are a highly skilled network analyst. Your task is to analyze a batch of raw network log entries and generate a comprehensive output that includes both a detailed plain-text summary and a structured JSON summary.

The user provided a query, and the following raw log entries were retrieved from the database:
---
{logs}
---
Analyze these logs and provide ALL output in a single JSON object that conforms exactly to the schema provided below.
The 'summary_text' field must contain the detailed natural language analysis.

Schema and Formatting Instructions:
----------------------------------
{format_instructions}
----------------------------------
"""

summary_prompt = PromptTemplate(
    template = SUMMARY_TEMPLATE,
    input_variables=["logs"],
    partial_variables={"format_instructions": parser_instructions}
)

#summarization chain
summarization_chain = summary_prompt | llm | parser


def get_log_summary(user_question):
    """
    Coordinates the entire process: SQL Query -> Data Fetch -> Structured Summarization.
    Returns the parsed Python dictionary (which includes both text and JSON data).
    """
    print(f"\n -- STEP 1: Running SQL agent for: '{user_question}' ---\n ")

    raw_logs_responses = agent_executor.invoke({"input": user_question})
    raw_logs = raw_logs_responses['output']

    if not raw_logs or raw_logs.strip() == "[]":
        return {"summary_text": "The query returned no log entries to summarize.", "timeframe": "N/A", "events": []}

    print("\n -- STEP 2: Raw logs retrieved. Generating Structured Summary... -- \n")

    # The chain now returns the final Python dictionary/Pydantic object
    final_summary_dict = summarization_chain.invoke({"logs": raw_logs})

    return final_summary_dict


# --- FINAL EXECUTION (Updated Output Handling) ---

user_input = "Retrieve all log entries from Router1, SwitchA, Firewall and Router2, and then summarize the key events"

print("\n\n==============================================")
print("NETWORK LOG SUMMARIZER AGENT START")
print("==============================================")

# Execute the combined process
final_structured_output = get_log_summary(user_input)

# ------------------------------------------------
# Output Formatting (Step 5.1 & 5.2 implementation)
# ------------------------------------------------

import json

print("\n==============================================")
print("1. PLAIN ENGLISH SUMMARY (Extracted from JSON)")
print("==============================================")
print(final_structured_output.get('summary_text', 'No summary text found.'))

print("\n==============================================")
print("2. JSON OUTPUT FOR DASHBOARDS")
print("==============================================")
# Print the JSON output neatly formatted
print(json.dumps(final_structured_output, indent=2))
print("==============================================")