from typing import Optional, List, Dict, Any
from langchain_core.tools import tool
from app import schemas

@tool("log_interaction", args_schema=schemas.LogInteractionInput)
def log_interaction_tool(
    hcp_name: str,
    interaction_type: str,
    topics_discussed: str,
    observed_sentiment: str,
    date: Optional[str] = None,
    time: Optional[str] = None,
    attendees: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None,
    products: Optional[List[str]] = None,
    materials: Optional[List[str]] = None,
    samples: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Log a new Healthcare Professional (HCP) interaction record in the database.
    Captures topics discussed, products, shared materials, samples distributed, sentiment, and follow-ups.
    """
    from app.database import SessionLocal
    from app import crud
    
    input_data = schemas.LogInteractionInput(
        hcp_name=hcp_name,
        interaction_type=interaction_type,
        date=date,
        time=time,
        topics_discussed=topics_discussed,
        observed_sentiment=observed_sentiment,
        attendees=attendees,
        outcomes=outcomes,
        follow_up_actions=follow_up_actions,
        products=products,
        materials=materials,
        samples=samples
    )
    
    with SessionLocal() as db:
        try:
            interaction = crud.log_interaction_transactional(db, input_data)
            return {
                "status": "success",
                "interaction_id": interaction.id,
                "message": f"Successfully logged interaction with {interaction.hcp.name}.",
                "data": {
                    "hcp_name": interaction.hcp.name,
                    "interaction_type": interaction.interaction_type,
                    "date": interaction.date.strftime("%Y-%m-%d"),
                    "time": interaction.time.strftime("%H:%M"),
                    "topics_discussed": interaction.topics_discussed,
                    "observed_sentiment": interaction.observed_sentiment,
                    "outcomes": interaction.outcomes,
                    "follow_up_actions": interaction.follow_up_actions,
                    "products": [p.name for p in interaction.products],
                    "materials": [m.name for m in interaction.materials],
                    "samples": [{"name": assoc.sample.name, "quantity": assoc.quantity} for assoc in interaction.samples_association],
                    "attendees": interaction.attendees
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


@tool("edit_interaction", args_schema=schemas.EditInteractionInput)
def edit_interaction_tool(
    interaction_id: Optional[int] = None,
    hcp_name: Optional[str] = None,
    observed_sentiment: Optional[str] = None,
    topics_discussed: Optional[str] = None,
    interaction_type: Optional[str] = None,
    date: Optional[str] = None,
    time: Optional[str] = None,
    outcomes: Optional[str] = None,
    follow_up_actions: Optional[str] = None
) -> Dict[str, Any]:
    """
    Modify or edit details on an existing interaction record.
    Specify what whitelisted fields to change (topics, outcomes, sentiment, follow-ups, date/time).
    """
    from app.database import SessionLocal
    from app import crud
    
    input_data = schemas.EditInteractionInput(
        interaction_id=interaction_id,
        hcp_name=hcp_name,
        observed_sentiment=observed_sentiment,
        topics_discussed=topics_discussed,
        interaction_type=interaction_type,
        date=date,
        time=time,
        outcomes=outcomes,
        follow_up_actions=follow_up_actions
    )
    
    with SessionLocal() as db:
        try:
            interaction = crud.edit_interaction_transactional(db, input_data)
            return {
                "status": "success",
                "interaction_id": interaction.id,
                "message": f"Successfully updated interaction #{interaction.id} for {interaction.hcp.name}.",
                "data": {
                    "hcp_name": interaction.hcp.name,
                    "interaction_type": interaction.interaction_type,
                    "date": interaction.date.strftime("%Y-%m-%d"),
                    "time": interaction.time.strftime("%H:%M"),
                    "topics_discussed": interaction.topics_discussed,
                    "observed_sentiment": interaction.observed_sentiment,
                    "outcomes": interaction.outcomes,
                    "follow_up_actions": interaction.follow_up_actions,
                    "products": [p.name for p in interaction.products],
                    "materials": [m.name for m in interaction.materials],
                    "samples": [{"name": assoc.sample.name, "quantity": assoc.quantity} for assoc in interaction.samples_association],
                    "attendees": interaction.attendees
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


@tool("get_hcp_context", args_schema=schemas.GetHCPContextInput)
def get_hcp_context_tool(hcp_name: str) -> Dict[str, Any]:
    """
    Retrieve profile details, recent historical interactions, preferences, and pending follow-ups for a specific doctor.
    """
    from app.database import SessionLocal
    from app import crud
    
    with SessionLocal() as db:
        try:
            context = crud.get_hcp_context(db, hcp_name)
            return {
                "status": "success",
                "message": f"Successfully retrieved profile context for {context['name']}.",
                "data": context
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


@tool("search_interactions", args_schema=schemas.SearchInteractionsInput)
def search_interactions_tool(
    query: Optional[str] = None,
    limit: Optional[int] = 5
) -> Dict[str, Any]:
    """
    Search historical logs of meetings, calls, and email interactions by keyword.
    """
    from app.database import SessionLocal
    from app import crud
    
    with SessionLocal() as db:
        try:
            results = crud.search_interactions(db, query, limit)
            return {
                "status": "success",
                "message": f"Found {len(results)} matching interactions.",
                "data": results
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


@tool("suggest_follow_up", args_schema=schemas.SuggestFollowUpInput)
def suggest_follow_up_tool(
    interaction_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generates recommended follow-up actions, templates, and next steps for the active interaction.
    """
    from app.database import SessionLocal
    from app import models
    
    with SessionLocal() as db:
        try:
            # Retrieve active or last interaction
            if interaction_id:
                inter = db.query(models.Interaction).filter(models.Interaction.id == interaction_id).first()
            else:
                inter = db.query(models.Interaction).order_by(models.Interaction.created_at.desc()).first()
                
            if not inter:
                return {
                    "status": "error",
                    "message": "No active interaction to suggest follow-ups for. Please log an interaction first."
                }
            
            # Simple rule-based/templated AI suggestions based on interaction content
            hcp_name = inter.hcp.name
            specialty = inter.hcp.specialty
            products = [p.name for p in inter.products]
            materials = [m.name for m in inter.materials]
            
            suggestions = []
            
            # 1. Schedule a follow-up meeting recommendation
            suggestions.append({
                "type": "schedule",
                "action": "Schedule follow-up meeting in 2 weeks",
                "description": f"Schedule follow-up appointment with {hcp_name} to review patient response to starter packs.",
                "details": {
                    "title": f"Follow-up with {hcp_name}",
                    "in_days": 14,
                    "hcp_id": inter.hcp_id
                }
            })
            
            # 2. Materials specific recommendation
            if "OncoBoost 50mg" in products:
                suggestions.append({
                    "type": "email",
                    "action": "Send OncoBoost Phase III Trial Report PDF",
                    "description": f"Email the OncoBoost Phase III clinical sheets requested by {hcp_name}.",
                    "details": {
                        "to": inter.hcp.email or "doctor@hospital.com",
                        "subject": "OncoBoost Phase III Clinical Trial Reports",
                        "body": f"Dear {hcp_name},\n\nAs discussed during our meeting today, please find attached the OncoBoost Phase III clinical reports. Please let me know if you have any questions.\n\nBest regards,\nMedical Rep"
                    }
                })
            else:
                # Default material mail
                suggestions.append({
                    "type": "email",
                    "action": "Send Clinical Literature Email",
                    "description": f"Email product literature and prescribing information to {hcp_name}.",
                    "details": {
                        "to": inter.hcp.email or "doctor@hospital.com",
                        "subject": "Product Prescribing Information & Patient Guides",
                        "body": f"Dear {hcp_name},\n\nThank you for your time today. As discussed, I am sharing our latest patient guide brochures. Please let me know if you require more samples.\n\nBest regards,\nMedical Rep"
                    }
                })
                
            # 3. Custom invitation / Advisory board invite
            if inter.observed_sentiment == "Positive":
                suggestions.append({
                    "type": "task",
                    "action": f"Invite {hcp_name} to Advisory Board list",
                    "description": f"Add {hcp_name} ({specialty}) to the list of potential advisory board participants for upcoming medical forums.",
                    "details": {
                        "task_name": f"Advisory Board nomination - {hcp_name}",
                        "priority": "High"
                    }
                })
            else:
                suggestions.append({
                    "type": "task",
                    "action": f"Nominate {hcp_name} for regional seminar",
                    "description": f"Add {hcp_name} to the list of invitees for the upcoming seminar series.",
                    "details": {
                        "task_name": f"Seminar invite list - {hcp_name}",
                        "priority": "Medium"
                    }
                })
                
            return {
                "status": "success",
                "message": "Generated 3 follow-up recommendations successfully.",
                "data": {
                    "interaction_id": inter.id,
                    "hcp_name": hcp_name,
                    "suggestions": suggestions
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }


@tool("manage_samples_and_materials", args_schema=schemas.ManageSamplesInput)
def manage_samples_and_materials_tool(action: str) -> Dict[str, Any]:
    """
    Retrieve inventory status for medicinal samples or available shared literature brochures.
    Use 'list_samples' to check sample inventory, and 'list_materials' to check brochures.
    """
    from app.database import SessionLocal
    from app import models
    
    with SessionLocal() as db:
        try:
            if action == "list_samples":
                samples = db.query(models.Sample).all()
                data = [{"id": s.id, "name": s.name, "stock_quantity": s.stock_quantity} for s in samples]
                msg = "Successfully loaded sample inventory."
            elif action == "list_materials":
                materials = db.query(models.Material).all()
                data = [{"id": m.id, "name": m.name, "type": m.type} for m in materials]
                msg = "Successfully loaded shared materials list."
            else:
                raise ValueError(f"Unknown inventory action: {action}. Must be list_samples or list_materials")
                
            return {
                "status": "success",
                "message": msg,
                "data": data
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
