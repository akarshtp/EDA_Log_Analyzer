# EDA Log Analyzer

A Python tool that uses **Gemini 2.5 Flash** to analyze EDA timing logs. It parses setup violations and suggests technical fixes for VLSI design.

## Features
* Extracts Startpoint, Endpoint, and Slack from `.log` files.
* Generates AI diagnostics for timing violations.
* Uses `.env` for secure API key management.

## How to Run
1. Install dependencies: `pip install -r requirements.txt`
2. Add your API key to a `.env` file: `GOOGLE_API_KEY=your_key_here`
3. Run the script: `python eda_analyzer.py`