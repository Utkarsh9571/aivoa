import os
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app import models, schemas, crud
from app.database import engine, get_db, SessionLocal
from app.agent.graph import execute_agent

# Initialize FastAPI
app = FastAPI(
    title="AI-First CRM HCP Module API",
    description="Backend API for Healthcare Professional (HCP) Interaction Log Module",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development and demo
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Health endpoint
@app.get("/api/health", response_model=schemas.HealthResponse, tags=["Diagnostics"])
def health_check(db: Session = Depends(get_db)):
    """
    Checks the health of the application and the connection to the database.
    """
    try:
        # Run a simple query to verify database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
        
    return schemas.HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status
    )

# Autocomplete metadata endpoint
@app.get("/api/metadata", response_model=schemas.MetadataResponse, tags=["CRM Metadata"])
def get_metadata(db: Session = Depends(get_db)):
    """
    Returns full list of HCPs, Products, Materials, and Samples to populate form selectors.
    """
    try:
        data = crud.get_metadata(db)
        return schemas.MetadataResponse(
            hcps=[schemas.HCPResponse.model_validate(h) for h in data["hcps"]],
            products=[schemas.ProductResponse.model_validate(p) for p in data["products"]],
            materials=[schemas.MaterialResponse.model_validate(m) for m in data["materials"]],
            samples=[schemas.SampleResponse.model_validate(s) for s in data["samples"]]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database failure: {str(e)}"
        )

# Get recent interactions endpoint
@app.get("/api/interactions", tags=["Interactions"])
def get_recent_interactions(limit: int = 10, db: Session = Depends(get_db)):
    """
    Retrieve history of recently logged interactions.
    """
    try:
        return crud.search_interactions(db, query=None, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database failure: {str(e)}"
        )

# Manual create endpoint
@app.post("/api/interactions", tags=["Interactions"])
def create_interaction_manually(req: schemas.ManualCreateInteractionRequest, db: Session = Depends(get_db)):
    """
    Log an interaction manually via the structured form on the UI.
    """
    try:
        interaction = crud.manual_create_interaction(db, req)
        return {
            "status": "success",
            "message": f"Successfully logged interaction with {interaction.hcp.name}.",
            "interaction_id": interaction.id
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during manual save: {str(e)}"
        )

# Manual edit endpoint
@app.put("/api/interactions/{id}", tags=["Interactions"])
def edit_interaction_manually(id: int, req: schemas.ManualEditInteractionRequest, db: Session = Depends(get_db)):
    """
    Edit/Modify an interaction manually.
    """
    try:
        interaction = crud.manual_edit_interaction(db, id, req)
        return {
            "status": "success",
            "message": f"Successfully updated interaction #{interaction.id}.",
            "interaction_id": interaction.id
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error during edit: {str(e)}"
        )

# Conversational AI Chat Endpoint
@app.post("/api/chat", response_model=schemas.ChatResponse, tags=["Conversational AI"])
def chat_with_copilot(req: schemas.ChatRequest):
    """
    Core conversational endpoint. Runs the LangGraph agent workflow to identify intent,
    execute tools (database transactions), and synchronize the frontend form.
    """
    try:
        result = execute_agent(req.message, req.current_interaction_id)
        return schemas.ChatResponse(
            response=result["response"],
            current_interaction_id=result["current_interaction_id"],
            form_data=result["form_data"],
            hcp_context=result["hcp_context"],
            tool_calls=result["tool_calls"]
        )
    except Exception as e:
        # Fallback summary response if execution hits a severe error
        return schemas.ChatResponse(
            response=f"I encountered a server-side error processing your request: {str(e)}",
            current_interaction_id=req.current_interaction_id,
            form_data=None,
            hcp_context=None,
            tool_calls=[schemas.ToolCallRecord(
                name="execute_agent",
                args={"message": req.message},
                status="error",
                result=str(e)
            )]
        )
