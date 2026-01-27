"""
Chat History Model
Stores chat messages with support for HITL (Human-in-the-Loop) data
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, func
from sqlalchemy.orm import relationship
from models import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    
    # Message content
    role = Column(String(50), nullable=False)  # 'user', 'assistant', 'system', 'tool'
    content = Column(Text, nullable=True)
    
    # Tool and HITL support
    tool_type = Column(String(100), nullable=True)  # e.g., 'check_calendar', 'form_input'
    tool_call_id = Column(String(255), nullable=True)
    tool_name = Column(String(255), nullable=True)
    tool_arguments = Column(JSON, nullable=True)
    tool_result = Column(JSON, nullable=True)
    
    # Human-in-the-Loop data
    hitl_type = Column(String(50), nullable=True)  # 'form', 'confirmation', None
    hitl_schema = Column(JSON, nullable=True)  # Schema for form fields or confirmation options
    hitl_response = Column(JSON, nullable=True)  # User's response to HITL prompt
    hitl_status = Column(String(50), nullable=True)  # 'pending', 'submitted', 'approved', 'rejected'
    
    # Metadata
    citations = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, session='{self.session_id}', role='{self.role}')>"

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "tool_type": self.tool_type,
            "hitl_type": self.hitl_type,
            "hitl_schema": self.hitl_schema,
            "hitl_response": self.hitl_response,
            "hitl_status": self.hitl_status,
            "citations": self.citations,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
