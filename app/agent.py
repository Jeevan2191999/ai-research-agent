import os
import anthropic
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

tools = [
    {
        "name": "web_search",
        "description": "Search the web for current information on a topic. Use this to find relevant sources and information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_url",
        "description": "Read the content of a webpage URL. Use this to get detailed information from a specific source.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to read"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "summarise_findings",
        "description": "Summarise and synthesise all research findings into a structured report. Use this as the final step.",
        "input_schema": {
            "type": "object",
            "properties": {
                "findings": {
                    "type": "string",
                    "description": "All the research findings to summarise"
                },
                "question": {
                    "type": "string",
                    "description": "The original research question"
                }
            },
            "required": ["findings", "question"]
        }
    }
]

def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "No results found for this query."
        output = f"Search results for: {query}\n\n"
        for i, r in enumerate(results, 1):
            output += f"{i}. {r.get('title', 'No title')}\n"
            output += f"   URL: {r.get('href', 'No URL')}\n"
            output += f"   Summary: {r.get('body', 'No summary')[:200]}\n\n"
        return output
    except Exception as e:
        return f"Search failed: {str(e)}"

def read_url(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = " ".join(text.split())
        return text[:3000] + "..." if len(text) > 3000 else text
    except Exception as e:
        return f"Could not read URL: {str(e)}"

def summarise_findings(findings: str, question: str) -> str:
    return f"Research complete for: {question}\n\n{findings}"

def process_tool_call(tool_name: str, tool_input: dict) -> str:
    if tool_name == "web_search":
        return web_search(tool_input["query"])
    elif tool_name == "read_url":
        return read_url(tool_input["url"])
    elif tool_name == "summarise_findings":
        return summarise_findings(tool_input["findings"], tool_input["question"])
    return "Unknown tool"

def run_research_agent(question: str):
    messages = [{"role": "user", "content": question}]
    system_prompt = """You are an autonomous research agent. When given a research question:
1. Search the web for relevant information using web_search
2. Read 2-3 of the most relevant URLs using read_url
3. Synthesise your findings using summarise_findings
4. Provide a clear, structured, well-cited report

Always cite your sources. Be thorough but concise. Flag any uncertainty clearly."""

    tool_calls_log = []
    sources = set()
    max_iterations = 10
    iteration = 0

    yield f"data: Starting research on: {question}\n\n"

    while iteration < max_iterations:
        iteration += 1
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=system_prompt,
            tools=tools,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            final_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    final_text += block.text
            yield f"data: FINAL:{final_text}\n\n"
            break

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    yield f"data: TOOL:{tool_name}:{list(tool_input.values())[0][:100]}\n\n"

                    result = process_tool_call(tool_name, tool_input)
                    tool_calls_log.append({
                        "tool": tool_name,
                        "input": str(tool_input),
                        "output": result[:500]
                    })

                    if tool_name == "read_url":
                        sources.add(tool_input.get("url", ""))

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            messages.append({"role": "user", "content": tool_results})

    yield f"data: DONE\n\n"
    return tool_calls_log, sources