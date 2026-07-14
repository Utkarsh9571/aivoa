import sys
import os
import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Add backend/ to Python path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app import models
from app.config import settings
from urllib.parse import urlparse, unquote

# Parse PostgreSQL credentials from DATABASE_URL
db_url = urlparse(settings.DATABASE_URL)
DB_USER = db_url.username or "postgres"
DB_PASSWORD = unquote(db_url.password) if db_url.password else ""
DB_HOST = db_url.hostname or "localhost"
DB_PORT = db_url.port or 9571
DB_NAME = db_url.path.lstrip('/') or "aivoa"

def ensure_database_exists():
    print(f"Connecting to default 'postgres' database on port {DB_PORT}...")
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database="postgres"
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # Check if database exists
    cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
    exists = cursor.fetchone()
    
    if not exists:
        print(f"Database '{DB_NAME}' does not exist. Creating...")
        cursor.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"Database '{DB_NAME}' created successfully.")
    else:
        print(f"Database '{DB_NAME}' already exists.")
        
    cursor.close()
    conn.close()

def seed_data():
    ensure_database_exists()
    
    print("Re-creating all database tables...")
    # Drop all tables first for a clean seed
    Base.metadata.drop_all(bind=engine)
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
    
    db = SessionLocal()
    try:
        print("Seeding database records...")
        
        # 1. HCPs
        hcps = [
            models.HCP(
                name="Dr. Rajesh Sharma",
                specialty="Cardiology",
                clinic_name="Metro Heart Institute",
                email="r.sharma@metroheart.com",
                phone="+91 98100 12345"
            ),
            models.HCP(
                name="Dr. Sarah Jenkins",
                specialty="Oncology",
                clinic_name="St. Jude Medical Center",
                email="s.jenkins@stjude.org",
                phone="+1 (555) 019-2834"
            ),
            models.HCP(
                name="Dr. Amit Patel",
                specialty="Endocrinology",
                clinic_name="Apex Diabetes Care",
                email="apatel@apexdiabetes.com",
                phone="+91 99588 54321"
            )
        ]
        db.add_all(hcps)
        db.flush() # flush to get primary keys
        
        # 2. Products
        products = [
            models.Product(
                name="CardioFlow 10mg",
                description="Next-generation selective beta-blocker for hypertension and cardiovascular risk reduction.",
                therapeutic_area="Cardiovascular"
            ),
            models.Product(
                name="OncoBoost 50mg",
                description="Targeted small-molecule kinase inhibitor for advanced solid tumors.",
                therapeutic_area="Oncology"
            ),
            models.Product(
                name="GlycaStop 5mg",
                description="High-efficacy oral hypoglycemic agent for glycemic control in Type 2 Diabetes.",
                therapeutic_area="Endocrinology"
            )
        ]
        db.add_all(products)
        
        # 3. Materials
        materials = [
            models.Material(name="Cardiology Patient Guide", type="Brochure"),
            models.Material(name="OncoBoost Phase III Trial Report", type="PDF Document"),
            models.Material(name="GlycaStop Prescribing Information", type="PDF Document")
        ]
        db.add_all(materials)
        
        # 4. Samples
        samples = [
            models.Sample(name="CardioFlow 10mg Sample Pack", stock_quantity=100),
            models.Sample(name="OncoBoost 50mg Sample Pack", stock_quantity=50),
            models.Sample(name="GlycaStop 5mg Starter Kit", stock_quantity=200)
        ]
        db.add_all(samples)
        db.flush()
        
        # 5. Seed historical interactions for Dr. Rajesh Sharma and Dr. Sarah Jenkins
        # Dr. Sharma - Interaction 1 (Meeting 2 weeks ago)
        date_sharma_1 = datetime.date.today() - datetime.timedelta(days=14)
        inter_sharma_1 = models.Interaction(
            hcp_id=hcps[0].id,
            interaction_type="Meeting",
            date=date_sharma_1,
            time=datetime.time(10, 30),
            attendees="Dr. Rajesh Sharma, Rep (Self)",
            topics_discussed="Discussed clinical trial results of CardioFlow 10mg vs competitor. Patient compliance is high.",
            observed_sentiment="Positive",
            outcomes="Dr. Sharma agreed to prescribe CardioFlow to 5 new mild hypertension patients.",
            follow_up_actions="Send detailed clinical study PDF.",
            ai_summary="Logged historical meeting with Dr. Rajesh Sharma discussing CardioFlow compliance."
        )
        db.add(inter_sharma_1)
        
        # Dr. Jenkins - Interaction 1 (Call 1 week ago)
        date_jenkins_1 = datetime.date.today() - datetime.timedelta(days=7)
        inter_jenkins_1 = models.Interaction(
            hcp_id=hcps[1].id,
            interaction_type="Call",
            date=date_jenkins_1,
            time=datetime.time(14, 15),
            attendees="Dr. Sarah Jenkins, Rep (Self)",
            topics_discussed="Brief call to check on patient feedback for OncoBoost 50mg starter packs.",
            observed_sentiment="Neutral",
            outcomes="Dr. Jenkins requested the Phase III study data sheets to verify overall survival rate.",
            follow_up_actions="Share OncoBoost Phase III trial data sheets next week.",
            ai_summary="Logged historical call with Dr. Sarah Jenkins requesting survival rate clinical sheets."
        )
        db.add(inter_jenkins_1)
        db.flush()
        
        # Add associations for historical data
        # Sharma discussed CardioFlow
        inter_sharma_1.products.append(products[0])
        # Sharma received Cardiology Patient Guide
        inter_sharma_1.materials.append(materials[0])
        # Sharma received 2 CardioFlow samples
        assoc_sharma = models.InteractionSample(
            interaction_id=inter_sharma_1.id,
            sample_id=samples[0].id,
            quantity=2
        )
        db.add(assoc_sharma)
        # Deduct stock
        samples[0].stock_quantity -= 2
        
        # Jenkins discussed OncoBoost
        inter_jenkins_1.products.append(products[1])
        
        # Add follow-up records
        follow_sharma = models.FollowUp(
            interaction_id=inter_sharma_1.id,
            description="Send detailed clinical study PDF.",
            due_date=date_sharma_1 + datetime.timedelta(days=7),
            status="Completed"
        )
        follow_jenkins = models.FollowUp(
            interaction_id=inter_jenkins_1.id,
            description="Share OncoBoost Phase III trial data sheets next week.",
            due_date=date_jenkins_1 + datetime.timedelta(days=7),
            status="Pending"
        )
        db.add_all([follow_sharma, follow_jenkins])
        
        db.commit()
        print("Database seeded successfully with realistic clinic and representative data!")
        
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
