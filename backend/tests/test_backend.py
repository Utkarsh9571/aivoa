import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import date

from app import models, schemas, crud

# Setup isolated SQLite in-memory DB for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db():
    # Create tables
    models.Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Seed basic records for testing
    hcp = models.HCP(
        name="Dr. Tester",
        specialty="General",
        clinic_name="Test Clinic",
        email="tester@clinic.com",
        phone="1234567890"
    )
    prod = models.Product(
        name="TestProduct 10mg",
        therapeutic_area="TestArea"
    )
    mat = models.Material(
        name="Test Brochure",
        type="Brochure"
    )
    sample = models.Sample(
        name="TestSample Pack",
        stock_quantity=10  # Seed with 10 items
    )
    
    session.add_all([hcp, prod, mat, sample])
    session.commit()
    
    try:
        yield session
    finally:
        session.close()
        # Drop tables
        models.Base.metadata.drop_all(bind=engine)


def test_log_interaction_success(db):
    """
    Verifies that log_interaction completes successfully,
    associates entities, and deducts sample inventory.
    """
    input_data = schemas.LogInteractionInput(
        hcp_name="Dr. Tester",
        interaction_type="Meeting",
        topics_discussed="Discussed TestProduct benefits.",
        observed_sentiment="Positive",
        products=["TestProduct 10mg"],
        materials=["Test Brochure"],
        samples=[{"name": "TestSample Pack", "quantity": 3}],
        follow_up_actions="Follow up next week."
    )
    
    interaction = crud.log_interaction_transactional(db, input_data)
    
    assert interaction.id is not None
    assert interaction.hcp.name == "Dr. Tester"
    assert interaction.observed_sentiment == "Positive"
    assert len(interaction.products) == 1
    assert interaction.products[0].name == "TestProduct 10mg"
    assert len(interaction.materials) == 1
    
    # Check sample association and inventory deduction
    assert len(interaction.samples_association) == 1
    assert interaction.samples_association[0].quantity == 3
    
    # Check stock deduction (10 - 3 = 7)
    sample = db.query(models.Sample).filter(models.Sample.name == "TestSample Pack").first()
    assert sample.stock_quantity == 7


def test_log_interaction_insufficient_stock(db):
    """
    Verifies that if sample stock is insufficient, log_interaction
    raises a ValueError and transactionally rolls back all modifications.
    """
    input_data = schemas.LogInteractionInput(
        hcp_name="Dr. Tester",
        interaction_type="Meeting",
        topics_discussed="Discussed benefits.",
        observed_sentiment="Positive",
        products=["TestProduct 10mg"],
        samples=[{"name": "TestSample Pack", "quantity": 15}] # 15 requested, only 10 in stock
    )
    
    with pytest.raises(ValueError) as excinfo:
        crud.log_interaction_transactional(db, input_data)
        
    assert "Insufficient stock for sample" in str(excinfo.value)
    
    # Verify no interaction record was created (rolled back!)
    interactions_count = db.query(models.Interaction).count()
    assert interactions_count == 0
    
    # Verify stock remained at 10
    sample = db.query(models.Sample).filter(models.Sample.name == "TestSample Pack").first()
    assert sample.stock_quantity == 10


def test_edit_interaction(db):
    """
    Verifies that edit_interaction modifies whitelisted fields
    correctly on the database.
    """
    # 1. Log an interaction first
    log_input = schemas.LogInteractionInput(
        hcp_name="Dr. Tester",
        interaction_type="Call",
        topics_discussed="Initial discussion.",
        observed_sentiment="Neutral",
        follow_up_actions="Call tomorrow."
    )
    inter = crud.log_interaction_transactional(db, log_input)
    assert inter.observed_sentiment == "Neutral"
    
    # 2. Modify whitelisted fields
    edit_input = schemas.EditInteractionInput(
        interaction_id=inter.id,
        observed_sentiment="Positive",
        topics_discussed="Follow-up discussion completed.",
        follow_up_actions="No further action."
    )
    updated_inter = crud.edit_interaction_transactional(db, edit_input)
    
    assert updated_inter.id == inter.id
    assert updated_inter.observed_sentiment == "Positive"
    assert updated_inter.topics_discussed == "Follow-up discussion completed."
    assert updated_inter.follow_up_actions == "No further action."
