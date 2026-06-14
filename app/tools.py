import os
import glob
import pandas as pd
from typing import Optional, Dict, Any, List
from app.db import search_pages, read_page
from app.executor import execute_python_code
from app.config import WORKSPACE_DIR, ARTIFACTS_DIR

CSV_DIR = os.path.join(WORKSPACE_DIR, "data")

def list_available_csvs() -> Dict[str, Any]:
    """
    List all parsed CSV datasets available in the workspace.
    Provides file paths, descriptions, and column schemas to help write code.
    """
    master_path = os.path.join(CSV_DIR, "census_master.csv")
    master_schema = []
    
    if os.path.exists(master_path):
        try:
            df = pd.read_csv(master_path, nrows=2)
            master_schema = list(df.columns)
        except Exception as e:
            master_schema = [f"Error reading schema: {e}"]
            
    # List individual tables
    state_csvs = {}
    for state in ["Karnataka", "Odisha", "Madhya Pradesh"]:
        state_dir = os.path.join(CSV_DIR, state)
        if os.path.exists(state_dir):
            files = [os.path.basename(f) for f in glob.glob(os.path.join(state_dir, "*.csv"))]
            state_csvs[state] = files
            
    return {
        "master_dataset": {
            "path": "data/census_master.csv",
            "description": "Unified flat dataset containing key district demographics for all three states (Karnataka, Odisha, MP). Best for cross-district comparisons, plotting growth, sorting by literacy rates, sex ratio, and worker distributions.",
            "columns": master_schema
        },
        "individual_tables": {
            "description": "Raw statement tables parsed from the documents, grouped by state. Each file corresponds to a statement page. Columns are indexed by col_0, col_1, etc. where col_0 is the district code, col_1 is district name, and subsequent columns contain specific tabular data from the report.",
            "available_by_state": state_csvs
        }
    }

def save_text_artifact(name: str, content: str, content_type: str = "markdown") -> str:
    """
    Save a text or markdown table artifact to the workspace.
    Returns a success message with the relative path.
    """
    # Clean the name to prevent directory traversal
    safe_name = os.path.basename(name)
    if not safe_name.endswith((".md", ".txt", ".csv", ".json")):
        if content_type == "markdown":
            safe_name += ".md"
        elif content_type == "csv":
            safe_name += ".csv"
        else:
            safe_name += ".txt"
            
    dest_path = os.path.join(ARTIFACTS_DIR, safe_name)
    
    try:
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Artifact successfully saved to workspace/artifacts/{safe_name}"
    except Exception as e:
        return f"Error saving artifact: {e}"

# Mapping schema for LLM tool definitions
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_pages",
            "description": "Search for matches across census document pages. Use multiple simple keywords (e.g. 'literacy rate Belgaum' or 'urban population Odisha'). Returns page numbers, state names, and snippets of text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords. Do not use complex query syntax, just plain space-separated words."
                    },
                    "state_filter": {
                        "type": "string",
                        "description": "Optional filter for state. Must be 'Karnataka', 'Odisha', or 'Madhya Pradesh'.",
                        "enum": ["Karnataka", "Odisha", "Madhya Pradesh"]
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_page",
            "description": "Read the full markdown content of a specific page from a census document to get detailed facts, tables, or notes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "state": {
                        "type": "string",
                        "description": "The state document to read. Must be 'Karnataka', 'Odisha', or 'Madhya Pradesh'.",
                        "enum": ["Karnataka", "Odisha", "Madhya Pradesh"]
                    },
                    "page_number": {
                        "type": "integer",
                        "description": "The page number to retrieve."
                    }
                },
                "required": ["state", "page_number"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_available_csvs",
            "description": "List the parsed CSV datasets available in the workspace. Returns the master census dataset schema (data/census_master.csv) and lists of separate table CSVs by state. Call this to check what variables and files are available before writing python code to analyze data.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "Execute a Python script to do calculations, process data, or generate Matplotlib charts. The code executes in the workspace directory. You can read 'data/census_master.csv' using pandas or list files. To save charts, always save them to 'artifacts/<filename>.png' (relative path). Returns standard output, standard error, exit code, and path to any generated artifacts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to run. Must be complete and self-contained."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_artifact",
            "description": "Save a structured output (like a markdown table, CSV, text report, or analysis) to the workspace artifacts directory. This allows the UI to display it cleanly.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Filename for the artifact (e.g. 'urban_rural_breakdown.md' or 'highest_sex_ratio.csv')."
                    },
                    "content": {
                        "type": "string",
                        "description": "The text or tabular content to save."
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Content format. Must be 'markdown', 'csv', or 'text'.",
                        "enum": ["markdown", "csv", "text"]
                    }
                },
                "required": ["name", "content"]
            }
        }
    }
]

def call_tool(name: str, args: Dict[str, Any]) -> Any:
    """
    Executes a tool by name with arguments.
    """
    if name == "search_pages":
        return search_pages(args["query"], args.get("state_filter"))
    elif name == "read_page":
        return read_page(args["state"], args["page_number"])
    elif name == "list_available_csvs":
        return list_available_csvs()
    elif name == "execute_python":
        return execute_python_code(args["code"])
    elif name == "save_artifact":
        return save_text_artifact(args["name"], args["content"], args.get("content_type", "markdown"))
    else:
        raise ValueError(f"Unknown tool name: {name}")
