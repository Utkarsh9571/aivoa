import sys
import json

from app.agent.graph import execute_agent
from app.database import SessionLocal
from app import models

def run_verification():
    print("==================================================")
    print("STARTING AUTOMATED VERIFICATION OF DEMO SCENARIOS")
    print("==================================================")
    
    db = SessionLocal()
    
    try:
        # Check initial stock
        sample = db.query(models.Sample).filter(models.Sample.name == "OncoBoost 50mg Sample Pack").first()
        if sample is None:
            raise ValueError("Sample 'OncoBoost 50mg Sample Pack' not found in database")
        initial_stock = sample.stock_quantity
        print(f"Initial OncoBoost Sample Stock: {initial_stock}")
        
        # ----------------------------------------------------------------------
        # SCENARIO 1: Conversational Interaction Logging
        # ----------------------------------------------------------------------
        print("\n[Scenario 1] Logging interaction conversationally...")
        note = "Met Dr. Sarah Jenkins today. We discussed OncoBoost 50mg. She was positive. Shared OncoBoost Phase III Trial Report and gave 3 samples. Follow up in two weeks."
        
        result = execute_agent(note, current_id=None)
        
        print("\nAgent Response:")
        print(result["response"])
        
        # Verify result structure
        assert result["current_interaction_id"] is not None, "Failed to get active interaction ID"
        assert result["form_data"] is not None, "Failed to get form synchronization payload"
        assert len(result["tool_calls"]) > 0, "No tools were executed"
        
        active_id = result["current_interaction_id"]
        print(f"\nSaved Interaction ID: #{active_id}")
        tool_call = result["tool_calls"][0]
        args = tool_call.args if hasattr(tool_call, "args") else tool_call["args"]
        print(json.dumps(args, indent=2))
        
        # Verify DB changes
        interaction = db.query(models.Interaction).filter(models.Interaction.id == active_id).first()
        assert interaction is not None, "Interaction record not found in DB"
        assert interaction.observed_sentiment == "Positive", "Sentiment mismatch"
        assert len(interaction.products) == 1, "Product count mismatch"
        assert interaction.products[0].name == "OncoBoost 50mg", "Product name mismatch"
        
        # Verify Stock Change (SCENARIO 4 part 1)
        db.refresh(sample)
        if sample is None:
            raise ValueError("Sample not found after refresh")
        print(f"Updated OncoBoost Sample Stock: {sample.stock_quantity}")
        assert sample.stock_quantity == initial_stock - 3, "Stock was not deducted correctly"
        print("[OK] Scenario 1 & 4 (Logging & Stock Change) verified successfully!")
        
        # ----------------------------------------------------------------------
        # SCENARIO 2: Conversational Edit of Active Interaction
        # ----------------------------------------------------------------------
        print("\n[Scenario 2] Editing active interaction conversationally...")
        edit_note = "Actually change the sentiment to neutral and add 'Check competitor pricing' to follow-up."
        
        edit_result = execute_agent(edit_note, current_id=active_id)
        
        print("\nAgent Response:")
        print(edit_result["response"])
        
        # Verify DB updates
        db.refresh(interaction)
        assert interaction.observed_sentiment == "Neutral", "Sentiment edit failed to persist"
        assert "Check competitor pricing" in interaction.follow_up_actions, "Follow-up edit failed to persist"
        print("[OK] Scenario 2 (Conversational Edit) verified successfully!")
        
        # ----------------------------------------------------------------------
        # SCENARIO 3: HCP Context Retrieval
        # ----------------------------------------------------------------------
        print("\n[Scenario 3] Retrieving HCP profile context...")
        profile_query = "Show me Dr. Sarah Jenkins profile and context."
        
        context_result = execute_agent(profile_query, current_id=active_id)
        
        print("\nAgent Response:")
        print(context_result["response"])
        
        assert context_result["hcp_context"] is not None, "HCP Context payload is missing"
        hcp_ctx = context_result["hcp_context"]
        print(f"\nLoaded Doctor: {hcp_ctx['name']} ({hcp_ctx['specialty']})")
        print(f"Clinic: {hcp_ctx['clinic_name']}")
        print(f"Number of recent interactions: {len(hcp_ctx['recent_interactions'])}")
        
        # Assert recent interaction history is populated
        assert len(hcp_ctx["recent_interactions"]) > 0, "No interaction history returned"
        print("[OK] Scenario 3 (HCP Context) verified successfully!")
        
        # ----------------------------------------------------------------------
        # SCENARIO 4: Inventory Lookup
        # ----------------------------------------------------------------------
        print("\n[Scenario 4] Checking inventory stocks...")
        inventory_query = "What samples do I have in stock?"
        
        inv_result = execute_agent(inventory_query, current_id=active_id)
        print("\nAgent Response:")
        print(inv_result["response"])
        assert len(inv_result["tool_calls"]) > 0, "No inventory tool call executed"
        print("[OK] Scenario 4 (Inventory Lookup) verified successfully!")
        
        print("\n==================================================")
        print("ALL DEMO SCENARIOS VERIFIED SUCCESSFULLY AND PERSISTED!")
        print("==================================================")
        
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    run_verification()
