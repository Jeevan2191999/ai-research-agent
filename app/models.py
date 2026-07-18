from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    report = Column(Text)
    sources_used = Column(Integer, default=0)
    tools_called = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer)
    tool_name = Column(String(100))
    tool_input = Column(Text)
    tool_output = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)