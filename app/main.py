from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db, create_tables
from app.models import ResearchSession, ToolCall
from app.agent import run_research_agent

app = FastAPI(title="Autonomous AI Research Agent", version="1.0.0")

@app.on_event("startup")
def startup():
    create_tables()
    print("AI Research Agent ready!")

class ResearchRequest(BaseModel):
    question: str

@app.get("/", response_class=HTMLResponse)
def home():
    return """<!DOCTYPE html>
<html>
<head>
    <title>AI Research Agent</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: Arial, sans-serif; background: #0a0a0a; color: #fff; min-height: 100vh; padding: 40px 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { font-size: 28px; margin-bottom: 8px; color: #6c63ff; }
        p { color: #888; margin-bottom: 30px; }
        .form-group { margin: 15px 0; }
        label { display: block; font-weight: bold; margin-bottom: 6px; color: #ccc; }
        textarea { width: 100%; padding: 12px; border: 1px solid #333; border-radius: 8px; font-size: 14px; font-family: Arial; background: #1a1a1a; color: #fff; height: 100px; resize: vertical; }
        button { background: #6c63ff; color: white; padding: 12px 30px; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 10px; }
        button:hover { background: #5a52d5; }
        button:disabled { background: #333; cursor: not-allowed; }
        #result { margin-top: 30px; }
        .tool-log { background: #111; border: 1px solid #222; border-radius: 8px; padding: 15px; margin: 10px 0; font-size: 13px; }
        .tool-item { color: #6c63ff; margin: 5px 0; }
        .tool-item span { color: #888; }
        .report { background: #1a1a1a; border: 1px solid #333; border-radius: 10px; padding: 25px; margin: 15px 0; line-height: 1.7; white-space: pre-wrap; font-size: 14px; color: #ccc; }
        .status { color: #888; font-size: 14px; margin: 10px 0; font-style: italic; }
        .section-title { color: #6c63ff; font-size: 16px; font-weight: bold; margin: 20px 0 10px; }
        .history-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #222; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Autonomous AI Research Agent</h1>
        <p>Ask any research question. The agent will autonomously search the web, read sources, and synthesise a structured report.</p>
        <div class="form-group">
            <label>Research Question</label>
            <textarea id="question" placeholder="e.g. What are the latest developments in AI safety in 2026?">What are the most in-demand AI engineering skills in 2026?</textarea>
        </div>
        <button id="researchBtn" onclick="startResearch()">Start Research</button>
        <button onclick="loadHistory()" style="background:#333; margin-left:10px;">View History</button>
        <div id="result"></div>
    </div>
    <script>
        function startResearch() {
            var question = document.getElementById('question').value;
            if (!question) { alert('Please enter a research question'); return; }
            var btn = document.getElementById('researchBtn');
            btn.disabled = true;
            btn.textContent = 'Researching... (60-90 seconds)';
            document.getElementById('result').innerHTML = '<div class="status">Agent is searching the web and reading sources. Please wait about 60 seconds...</div>';
            var xhr = new XMLHttpRequest();
            xhr.open('POST', '/research-sync', true);
            xhr.setRequestHeader('Content-Type', 'application/json');
            xhr.timeout = 180000;
            xhr.onload = function() {
                if (xhr.status === 200) {
                    var data = JSON.parse(xhr.responseText);
                    document.getElementById('result').innerHTML =
                        '<div class="section-title">Research Complete</div>' +
                        '<div class="report">' + data.report + '</div>' +
                        '<div class="tool-log"><div class="section-title">Tools Used</div>' +
                        data.tools.map(function(t) {
                            return '<div class="tool-item">Used: <strong>' + t.tool + '</strong> <span>' + t.input.substring(0, 80) + '</span></div>';
                        }).join('') +
                        '</div>';
                } else {
                    document.getElementById('result').innerHTML = '<div class="status" style="color:#ff6b6b">Error: ' + xhr.responseText + '</div>';
                }
                btn.disabled = false;
                btn.textContent = 'Start Research';
            };
            xhr.ontimeout = function() {
                document.getElementById('result').innerHTML = '<div class="status" style="color:#fbbf24">Timed out. Try a simpler question.</div>';
                btn.disabled = false;
                btn.textContent = 'Start Research';
            };
            xhr.onerror = function() {
                document.getElementById('result').innerHTML = '<div class="status" style="color:#ff6b6b">Connection failed.</div>';
                btn.disabled = false;
                btn.textContent = 'Start Research';
            };
            xhr.send(JSON.stringify({ question: question }));
        }

        function loadHistory() {
            var xhr = new XMLHttpRequest();
            xhr.open('GET', '/history', true);
            xhr.onload = function() {
                var data = JSON.parse(xhr.responseText);
                var resultDiv = document.getElementById('result');
                if (data.length === 0) {
                    resultDiv.innerHTML = '<div class="tool-log"><p>No research sessions yet.</p></div>';
                    return;
                }
                var html = '<div class="section-title">Research History</div><div class="tool-log">';
                data.forEach(function(s) {
                    html += '<div class="history-item"><span style="color:#ccc">' + s.question.substring(0, 80) + '...</span><span style="color:#888">' + s.created_at.substring(0, 10) + '</span></div>';
                });
                html += '</div>';
                resultDiv.innerHTML = html;
            };
            xhr.send();
        }
    </script>
</body>
</html>"""

@app.post("/research-sync")
def research_sync(request: ResearchRequest, db: Session = Depends(get_db)):
    tool_calls_log = []
    full_report = ""

    for event in run_research_agent(request.question):
        if "FINAL:" in event:
            full_report = event.replace("data: FINAL:", "").strip()
        elif "TOOL:" in event:
            parts = event.replace("data: TOOL:", "").strip().split(":")
            tool_calls_log.append({
                "tool": parts[0],
                "input": ":".join(parts[1:])
            })

    session = ResearchSession(
        question=request.question,
        report=full_report,
        sources_used=len([t for t in tool_calls_log if t["tool"] == "read_url"]),
        tools_called=len(tool_calls_log)
    )
    db.add(session)
    db.commit()

    return {
        "report": full_report,
        "tools": tool_calls_log,
        "question": request.question
    }

@app.get("/history")
def history(db: Session = Depends(get_db)):
    sessions = db.query(ResearchSession).order_by(
        ResearchSession.created_at.desc()
    ).limit(10).all()
    return [
        {
            "id": s.id,
            "question": s.question,
            "sources_used": s.sources_used,
            "created_at": str(s.created_at)
        }
        for s in sessions
    ]