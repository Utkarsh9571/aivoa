import datetime
from sqlalchemy import Table, Column, Integer, String, Text, Date, Time, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

# Simple many-to-many association tables
interaction_products = Table(
    "interaction_products",
    Base.metadata,
    Column("interaction_id", Integer, ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True),
    Column("product_id", Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
)

interaction_materials = Table(
    "interaction_materials",
    Base.metadata,
    Column("interaction_id", Integer, ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True),
    Column("material_id", Integer, ForeignKey("materials.id", ondelete="CASCADE"), primary_key=True)
)

# Association model for Samples (which includes a quantity)
class InteractionSample(Base):
    __tablename__ = "interaction_samples"
    
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True)
    sample_id = Column(Integer, ForeignKey("samples.id", ondelete="CASCADE"), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Relationships
    interaction = relationship("Interaction", back_populates="samples_association")
    sample = relationship("Sample", back_populates="interactions_association")


class HCP(Base):
    __tablename__ = "hcps"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    specialty = Column(String(255), nullable=False)
    clinic_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Relationships
    interactions = relationship("Interaction", back_populates="hcp", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    therapeutic_area = Column(String(255), nullable=False)


class Material(Base):
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    type = Column(String(100), nullable=False)  # Brochure, PDF, Video, etc.


class Sample(Base):
    __tablename__ = "samples"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    stock_quantity = Column(Integer, nullable=False, default=0)
    
    # Relationships
    interactions_association = relationship("InteractionSample", back_populates="sample", cascade="all, delete-orphan")


class Interaction(Base):
    __tablename__ = "interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcps.id", ondelete="CASCADE"), nullable=False)
    interaction_type = Column(String(100), nullable=False)  # Meeting, Email, Call, Video
    date = Column(Date, nullable=False, default=datetime.date.today)
    time = Column(Time, nullable=False, default=lambda: datetime.datetime.now().time())
    attendees = Column(Text, nullable=True)  # Comma separated list or raw text
    topics_discussed = Column(Text, nullable=True)
    observed_sentiment = Column(String(50), nullable=True)  # Positive, Neutral, Negative
    outcomes = Column(Text, nullable=True)
    follow_up_actions = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    hcp = relationship("HCP", back_populates="interactions")
    products = relationship("Product", secondary=interaction_products, backref="interactions")
    materials = relationship("Material", secondary=interaction_materials, backref="interactions")
    
    samples_association = relationship("InteractionSample", back_populates="interaction", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="interaction", cascade="all, delete-orphan")


class FollowUp(Base):
    __tablename__ = "follow_ups"
    
    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    due_date = Column(Date, nullable=True)
    status = Column(String(50), default="Pending")  # Pending, Completed
    
    # Relationships
    interaction = relationship("Interaction", back_populates="follow_ups")
