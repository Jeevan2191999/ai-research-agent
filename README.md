# Autonomous AI Research Agent

Live demo: https://ai-research-agent-u84i.onrender.com

An autonomous AI agent that searches the web, reads sources, and synthesises structured research reports using tool calling and the Anthropic Claude API.

## What It Does

- Takes any research question as input
- Autonomously searches the web using DuckDuckGo
- Reads and extracts content from relevant URLs
- Synthesises findings into a structured cited report
- Stores all research sessions in SQLite via SQLAlchemy
- Exposes a clean web interface via FastAPI

## Tech Stack

- Python, FastAPI, Anthropic Claude API
- Tool calling with web search and URL reading
- SQLAlchemy, SQLite
- Deployed on Render

## How to Run

git clone https://github.com/Jeevan2191999/ai-research-agent
cd ai-research-agent
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
echo "ANTHROPIC_API_KEY=your_key_here" > .env
uvicorn app.main:app --reload --port 8091
Open http://127.0.0.1:8091

## API Endpoints

- GET / - Web interface
- POST /research-sync - Run research session
- GET /history - View past sessions
