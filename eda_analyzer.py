import re
import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

# Load variables from .env into the system environment
load_dotenv() 

# Now LangChain will automatically find "GOOGLE_API_KEY" in the environment

def parse_timing_log(file_path):
    """Parses an EDA timing log and extracts critical metrics."""
    print("Parsing log file...")
    
    parsed_data = {
        "startpoint": None,
        "endpoint": None,
        "path_group": None,
        "slack": None,
        "status": "PASS"
    }
    
    try:
        with open(file_path, 'r') as file:
            log_content = file.read()
            
            # Extract Startpoint
            start_match = re.search(r'Startpoint:\s*([^\s]+)', log_content)
            if start_match:
                parsed_data["startpoint"] = start_match.group(1)
                
            # Extract Endpoint
            end_match = re.search(r'Endpoint:\s*([^\s]+)', log_content)
            if end_match:
                parsed_data["endpoint"] = end_match.group(1)
                
            # Extract Clock Domain / Path Group
            group_match = re.search(r'Path Group:\s*([^\s]+)', log_content)
            if group_match:
                parsed_data["path_group"] = group_match.group(1)
                
            # Extract Slack and check if violated
            slack_match = re.search(r'slack\s*\((VIOLATED|MET)\)\s*([-\d\.]+)', log_content)
            if slack_match:
                parsed_data["status"] = slack_match.group(1)
                parsed_data["slack"] = float(slack_match.group(2))
                
        return parsed_data
    except Exception as e:
        return f"Error reading log: {e}"

def generate_eda_diagnostics(parsed_data):
    """Uses Gemini Pro to analyze the structured error data and suggest fixes."""
    if parsed_data.get("status") != "VIOLATED":
        return "No timing violations found. Design meets constraints."
        
    print("Violation found. Initializing AI diagnostic sequence...")
    
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
    
    # Create the Prompt Template
    template = """
    You are an expert VLSI CAD & Physical Design Engineer. 
    Analyze the following Static Timing Analysis (STA) error data extracted from an EDA tool log:
    
    - Error Type: Setup Timing Violation
    - Startpoint: {startpoint}
    - Endpoint: {endpoint}
    - Clock Domain: {path_group}
    - Negative Slack: {slack} ns
    
    Provide a highly technical, bulleted list of 3 potential solutions to fix this setup violation. 
    Focus on practical RTL optimizations, synthesis constraints, and physical design techniques.
    Do not use conversational filler.
    """
    
    prompt = PromptTemplate(
        input_variables=["startpoint", "endpoint", "path_group", "slack"],
        template=template
    )
    
    # Chain the prompt and the model
    chain = prompt | llm
    
    # Execute the chain
    response = chain.invoke(parsed_data)
    return response.content

if __name__ == "__main__":
    log_file = "sta_timing_report.log"
    
    # 1. Parse the unstructured text into structured JSON data
    extracted_metrics = parse_timing_log(log_file)
    print("\n--- Structured JSON Output ---")
    print(json.dumps(extracted_metrics, indent=4))
    
    # 2. Pass the structured data to the LangChain pipeline
    if extracted_metrics.get("status") == "VIOLATED":
        print("\n--- Generating AI Diagnostics ---")
        ai_report = generate_eda_diagnostics(extracted_metrics)
        print(ai_report)