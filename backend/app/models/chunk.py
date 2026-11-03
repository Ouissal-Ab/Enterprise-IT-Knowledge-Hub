from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, ForeignKey, Integer, Text

from app.database.session import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position = Column(Integer, nullable=False)
    page = Column(Integer, nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(768), nullable=True)