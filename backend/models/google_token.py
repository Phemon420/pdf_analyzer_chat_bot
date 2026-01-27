"""
Google OAuth Token Model
Stores OAuth tokens for Google API access
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, ForeignKey, func
from sqlalchemy.orm import relationship
from models import Base


class GoogleToken(Base):
    __tablename__ = "google_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # OAuth tokens
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_type = Column(String(50), default="Bearer")
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Granted scopes
    scopes = Column(ARRAY(Text), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<GoogleToken(id={self.id}, user_id={self.user_id})>"

    def is_expired(self):
        """Check if access token is expired"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc) >= self.expires_at
