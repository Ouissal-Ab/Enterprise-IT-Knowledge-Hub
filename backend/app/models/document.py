from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.session import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)

    status = Column(String(20), default="pending", nullable=False)
    error_message = Column(Text, nullable=True)
    num_chunks = Column(Integer, default=0, nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="documents")