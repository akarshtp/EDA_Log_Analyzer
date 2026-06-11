# EDA Log Analyzer v2 — Universal, LLM-Powered

A Python tool that uses **Gemini 2.5 Flash** with **Pydantic structured output** to analyze EDA timing logs from **any tool** 



## Features

- **Universal Parsing** — Reads timing reports from Synopsys PrimeTime, Design Compiler, ICC2, Cadence Tempus/Innovus, and OpenSTA without any tool-specific code.
- **LLM-Powered Extraction** — Uses LangChain's `with_structured_output()` to force Gemini to return validated Pydantic models. Zero regex.
- **AI Diagnostics** — Generates root cause analysis and tool-specific TCL fix commands for timing violations.
- **Rich CLI Output** — Beautiful terminal display with colored tables, timing path visualization, and bottleneck highlighting.
- **Type-Safe** — All extracted data is validated through Pydantic v2 schemas.

## Project History (v1 vs. v2)



* **v1 (Legacy):** Initially built using complex Regex parsing to extract timing data. While functional, it was brittle and broke when EDA vendors changed their log formats slightly.
* **v2 (Current):** Completely re-architected into an LLM-powered extraction pipeline using LangChain and Pydantic. It now universally supports logs from Synopsys, Cadence, and OpenSTA without requiring any format-specific parsing code.

## Architecture

```
Log File → LLM Classifier → LLM Extractor → Pydantic Validation → AI Diagnostics → Rich CLI
              (identify tool)    (extract data)     (type-check)       (fix suggestions)
```

**How it works**: Instead of writing regex patterns for each EDA tool format, we use the LLM as the parser. The LLM reads the log like a human engineer would, then fills in a structured Pydantic form. Adding support for a new tool requires zero code changes.

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up your API key

Add your **free** Gemini API key to a `.env` file:

```
GOOGLE_API_KEY=your_key_here
```

Get a free key at [aistudio.google.com](https://aistudio.google.com/).

### 3. Run analysis

```bash
# Full analysis (classify → extract → diagnose)
python eda_analyzer.py analyze sta_timing_report.log

# Classify a log (quick check — 1 API call)
python eda_analyzer.py classify samples/tempus_timing.rpt

# JSON output
python eda_analyzer.py analyze samples/opensta_timing.rpt --json

# Verbose mode (show classification details)
python eda_analyzer.py analyze samples/primetime_setup.rpt -v
```

## Supported Tools

| Tool | Vendor | Format |
|------|--------|--------|
| PrimeTime | Synopsys | `Point / Incr / Path` with star-line headers |
| Design Compiler | Synopsys | Same as PrimeTime |
| ICC / ICC2 | Synopsys | Same as PrimeTime |
| Tempus | Cadence | `Instance / Cell / Arc / Edge` with Beginpoint |
| Innovus | Cadence | Same as Tempus |
| OpenSTA | Open Source | `Delay / Time / Description` with ^/v edges |



## Project Structure

```
├── eda_analyzer.py         # CLI entry point
├── models/
│   └── schemas.py          # Pydantic data models
├── core/
│   ├── extractor.py        # LLM extraction engine
│   ├── prompts.py          # Prompt templates
│   └── diagnostics.py      # AI diagnostics engine
├── samples/                # Test logs from different tools
│   ├── primetime_setup.rpt
│   ├── tempus_timing.rpt
│   └── opensta_timing.rpt
├── tests/                  # Unit tests
├── requirements.txt
└── .env                    # API key 
```

## Testing

```bash
# Schema validation tests
python -m pytest tests/test_schemas.py -v

# Full pipeline test (requires API key)
python -m pytest tests/test_extractor.py -v
```



## Tech Stack

- **LangChain** — LLM orchestration and structured output
- **Pydantic v2** — Data validation and type safety
- **Gemini 2.5 Flash** — LLM (free tier)
- **Rich** — Terminal formatting

## License

MIT License