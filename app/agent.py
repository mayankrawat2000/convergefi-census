import os
import json
import re
from openai import OpenAI
from typing import Dict, Any, List, Optional, Generator
from app.config import CEREBRAS_API_KEY, CEREBRAS_BASE_URL, DEFAULT_MODEL
from app.tools import TOOL_SCHEMAS, call_tool
from app.database import load_history, save_turn


def _parse_answer_partial(text_after_quote: str) -> str:
    """
    Given text immediately after the opening quote of the JSON "answer" field,
    extract the (possibly incomplete) string value, handling JSON escape sequences.
    Stops at the first unescaped closing quote.
    """
    result = []
    i = 0
    while i < len(text_after_quote):
        c = text_after_quote[i]
        if c == '\\' and i + 1 < len(text_after_quote):
            nc = text_after_quote[i + 1]
            escape_map = {'"': '"', 'n': '\n', 't': '\t', 'r': '\r',
                          '\\': '\\', '/': '/', 'b': '\b', 'f': '\f'}
            result.append(escape_map.get(nc, nc))
            i += 2
        elif c == '\\':
            # Incomplete escape at buffer boundary — stop here safely
            break
        elif c == '"':
            # Closing quote — answer field is fully received
            break
        else:
            result.append(c)
            i += 1
    return ''.join(result)




SYSTEM_PROMPT = """You are a highly analytical Census Research AI Assistant.
Your task is to answer user queries, summarize information, and generate artifacts (tables, charts) based on government census documents for Karnataka, Odisha, and Madhya Pradesh.

You have access to the following tools:
1. search_pages(query: str, state_filter: Optional[str]): Searches for keywords in the document pages and returns matching snippets.
2. read_page(state: str, page_number: int): Retrieves the full text of a specific page.
3. list_available_csvs(): Lists the structures and paths of parsed CSV files of tables in the workspace.
4. execute_python(code: str): Runs Python scripts. You can use this for arithmetic, data processing, sorting, or generating Matplotlib charts. Always make charts look premium and modern (add clear titles, axis labels, legend, use distinct markers/lines, and make it look clean). Always save charts to the relative path 'artifacts/chart_name.png' and NEVER call `plt.show()`.
5. save_artifact(name: str, content: str, content_type: str): Saves markdown tables or text reports to the artifacts folder.

Guidelines:
1. MEMORY: You are in a multi-turn chat. Earlier turns are provided in your context.
2. SOURCE CITATIONS: Every factual claim must be cited. When you make a claim, search the text to find the exact source page and snippet.
3. CODE EXECUTION: For calculations (sorting, comparing growth rates, percentages, gender ratios), list the available CSVs and write Python code using `pandas` to get exact mathematical answers. Do not guess or do mental math. If your code errors, review the traceback and modify your code to fix it.
4. UNANSWERABLE QUESTIONS: If the information is not present in the census files, explicitly and gracefully say so. Do not make up facts.
5. USER-FRIENDLY ANSWERS: In your markdown "answer" text, never output raw backend file paths (e.g., "artifacts/mp_population_growth.png"), raw datasets (e.g., "census_master.csv"), or system filenames/extensions (.png, .csv, .pdf). Refer to them in natural, user-friendly language (e.g., "the census dataset", "the generated bar chart", "the Madhya Pradesh census document"). Do not expose these raw paths or extensions to the user.
6. RESPONSE FORMAT: Your final response MUST be a single valid JSON object containing the fields:
   - "answer": A detailed markdown explanation of the findings.
   - "citations": A list of dicts with keys: "source_document" (e.g. "PC11_PCA_Data_Highlights_Karnataka.pdf"), "page_number" (int), and "snippet" (string).
   - "artifacts": A list of dicts with keys: "name" (filename of chart, markdown table, or CSV you saved/created), "type" (one of "image", "table", "document"), "description" (short string).

Example JSON final output format:
{
  "answer": "The literacy rate in Belgaum in 2011 was 73.48% (82.2% for males and 64.5% for females). Udupi had the highest sex ratio at 1094.",
  "citations": [
    {
      "source_document": "PC11_PCA_Data_Highlights_Karnataka.pdf",
      "page_number": 52,
      "snippet": "Belgaum district has registered a literacy rate of 73.48%"
    }
  ],
  "artifacts": [
    {
      "name": "karnataka_literacy_comparison.png",
      "type": "image",
      "description": "Chart comparing literacy rates across districts."
    }
  ]
}

Before returning your final response, ensure you output ONLY the valid JSON object (enclosed in curly braces). Do not prefix or suffix it with other text.
"""

class CensusAgent:
    def __init__(self, session_id: str, model: str = DEFAULT_MODEL, reasoning_effort: str = "medium"):
        self.session_id = session_id
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.client = OpenAI(
            api_key=CEREBRAS_API_KEY,
            base_url=CEREBRAS_BASE_URL
        )

    def _load_history(self) -> List[Dict[str, Any]]:
        """Load LLM context history from MongoDB."""
        return load_history(self.session_id)

    def clear_history(self):
        """History deletion is handled via the database module."""
        from app.database import delete_session
        delete_session(self.session_id)

    def extract_structured_json(self, raw_text: str) -> Dict[str, Any]:
        """
        Extracts JSON from agent's response, handling markdown blocks or surrounding text.
        """
        text = raw_text.strip()
        # Find first '{' and last '}'
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            json_str = text[start:end+1]
            try:
                return json.loads(json_str)
            except Exception as e:
                print(f"Failed to parse inner JSON: {e}")
                
        # Fallback if no JSON or invalid JSON found
        return {
            "answer": raw_text,
            "citations": [],
            "artifacts": []
        }

    def chat(self, user_message: str) -> Dict[str, Any]:
        history = self._load_history()
        
        # Build prompt list
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add conversation history
        for msg in history:
            # We only append user and assistant text messages to prevent payload explosion
            if msg["role"] in ("user", "assistant"):
                # If assistant message was structured JSON, only append the answer text to context
                content = msg["content"]
                if isinstance(content, str) and content.strip().startswith("{"):
                    try:
                        parsed = json.loads(content)
                        content = parsed.get("answer", content)
                    except:
                        pass
                messages.append({"role": msg["role"], "content": content})
                
        # Append current user message
        messages.append({"role": "user", "content": user_message})
        
        # Keep track of execution logs for debugging and transparency
        run_logs = []
        
        max_iterations = 10
        for i in range(max_iterations):
            run_logs.append(f"--- Iteration {i+1} ---")
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "tools": TOOL_SCHEMAS,
                    "tool_choice": "auto",
                    "temperature": 0.1 # Low temperature for factual consistency
                }
                if self.model in ("gpt-oss-120b", "zai-glm-4.7") and self.reasoning_effort:
                    kwargs["extra_body"] = {"reasoning_effort": self.reasoning_effort}
                response = self.client.chat.completions.create(**kwargs)
            except Exception as e:
                error_msg = f"LLM Call Failed: {e}"
                run_logs.append(error_msg)
                return {
                    "answer": f"Error occurred during LLM reasoning: {e}",
                    "citations": [],
                    "artifacts": [],
                    "logs": run_logs
                }
                
            assistant_msg = response.choices[0].message
            tool_calls = assistant_msg.tool_calls
            
            # If the model wants to chat or has finished reasoning without calling a tool
            if not tool_calls:
                run_logs.append("Assistant finished reasoning.")
                raw_response = assistant_msg.content or ""
                structured_response = self.extract_structured_json(raw_response)

                # Persist to MongoDB
                save_turn(
                    session_id=self.session_id,
                    user_message=user_message,
                    assistant_raw=raw_response,
                    citations=structured_response.get("citations", []),
                    artifacts=structured_response.get("artifacts", []),
                )

                # Return the final structured dict + logs
                structured_response["logs"] = run_logs
                return structured_response
                
            # If the model requested tool calls, we execute them
            run_logs.append(f"Assistant requested {len(tool_calls)} tool calls.")
            
            # Convert assistant message for context
            messages.append(assistant_msg)
            
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                run_logs.append(f"Calling tool: {tool_name} with arguments: {tool_args}")
                
                try:
                    tool_result = call_tool(tool_name, tool_args)
                    
                    # For execute_python, we format the output nicely for logs
                    if tool_name == "execute_python":
                        success_str = "Success" if tool_result["success"] else "Failed"
                        run_logs.append(f"Python execute result ({success_str}): stdout={tool_result['stdout'][:150]}... stderr={tool_result['stderr'][:150]}...")
                        if tool_result["artifacts"]:
                            run_logs.append(f"Generated artifacts: {tool_result['artifacts']}")
                    else:
                        res_str = str(tool_result)[:300]
                        run_logs.append(f"Tool response (truncated): {res_str}...")
                        
                except Exception as e:
                    tool_result = f"Error executing tool {tool_name}: {e}"
                    run_logs.append(tool_result)
                    
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                })
                
        # If we exceed max iterations
        run_logs.append("Exceeded maximum execution iterations.")
        return {
            "answer": "I apologized, but I reached my thinking limit trying to solve this. Please try clarifying your question.",
            "citations": [],
            "artifacts": [],
            "logs": run_logs
        }

    def stream_chat(self, user_message: str) -> Generator[str, None, None]:
        """
        Streaming variant of chat().
        Yields SSE-formatted strings:
          data: {"type": "tool",  "name": "<tool_name>"}
          data: {"type": "chunk", "text": "<partial answer text>"}
          data: {"type": "done",  "citations": [...], "artifacts": [...], "logs": [...]}
          data: {"type": "error", "message": "<msg>"}

        Tool-calling iterations use non-streaming calls (fast + simple).
        The FINAL answer call uses stream=True so the answer field is emitted
        token by token as it arrives from Cerebras.
        """
        def sse(obj: dict) -> str:
            return f"data: {json.dumps(obj)}\n\n"

        history = self._load_history()
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        for msg in history:
            if msg.get("role") in ("user", "assistant"):
                content = msg.get("content", "")
                # Strip outer JSON wrapper if assistant stored raw JSON
                if isinstance(content, str) and content.strip().startswith("{"):
                    try:
                        parsed = json.loads(content)
                        content = parsed.get("answer", content)
                    except Exception:
                        pass
                messages.append({"role": msg["role"], "content": content})

        messages.append({"role": "user", "content": user_message})
        run_logs: List[str] = []

        for iteration in range(10):
            run_logs.append(f"--- Iteration {iteration + 1} ---")

            # ── Non-streaming call for tool-use detection ─────────────────────
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "tools": TOOL_SCHEMAS,
                    "tool_choice": "auto",
                    "temperature": 0.1,
                }
                if self.model in ("gpt-oss-120b", "zai-glm-4.7") and self.reasoning_effort:
                    kwargs["extra_body"] = {"reasoning_effort": self.reasoning_effort}
                response = self.client.chat.completions.create(**kwargs)
            except Exception as e:
                yield sse({"type": "error", "message": str(e)})
                return

            assistant_msg = response.choices[0].message
            tool_calls = assistant_msg.tool_calls

            # ── No tool calls → this is the final answer; stream the clean parsed result ──
            if not tool_calls:
                run_logs.append("Assistant finished reasoning. Streaming final answer.")

                raw_response = assistant_msg.content or ""
                structured = self.extract_structured_json(raw_response)

                # Persist clean turn to MongoDB
                save_turn(
                    session_id=self.session_id,
                    user_message=user_message,
                    assistant_raw=raw_response,
                    citations=structured.get("citations", []),
                    artifacts=structured.get("artifacts", []),
                )

                # Stream the clean markdown answer token by token with a minor delay
                import time
                answer_text = structured.get("answer", "")
                chunk_size = 8
                for idx in range(0, len(answer_text), chunk_size):
                    chunk = answer_text[idx:idx+chunk_size]
                    yield sse({"type": "chunk", "text": chunk})
                    time.sleep(0.015)

                yield sse({
                    "type": "done",
                    "citations": structured.get("citations", []),
                    "artifacts": structured.get("artifacts", []),
                    "logs": run_logs,
                })
                return

            # ── Tool calls present → execute them ──────────────────────────────
            run_logs.append(f"Assistant requested {len(tool_calls)} tool call(s).")
            messages.append(assistant_msg)

            for tc in tool_calls:
                tool_name = tc.function.name
                try:
                    tool_args = json.loads(tc.function.arguments)
                except Exception:
                    tool_args = {}
                run_logs.append(f"Calling: {tool_name}")
                yield sse({
                    "type": "tool",
                    "name": tool_name,
                    "arguments": tool_args
                })

                try:
                    tool_result = call_tool(tool_name, tool_args)
                    if tool_name == "execute_python":
                        run_logs.append(
                            f"execute_python ({('OK' if tool_result['success'] else 'FAIL')}): "
                            f"artifacts={tool_result.get('artifacts', [])}"
                        )
                    else:
                        run_logs.append(f"{tool_name} result (truncated): {str(tool_result)[:200]}")
                except Exception as e:
                    tool_result = {"error": str(e)}
                    run_logs.append(f"Tool error: {e}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result),
                })

        run_logs.append("Exceeded maximum iterations.")
        yield sse({
            "type": "error",
            "message": "Reached my reasoning limit. Please try rephrasing your question.",
        })

