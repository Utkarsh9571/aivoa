from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Any, Optional
from datetime import date, time
import datetime

# Tool Inputs Schemas
class LogInteractionInput(BaseModel):
    hcp_name: str = Field(description="Name of the Healthcare Professional (e.g. Dr. Rajesh Sharma)")
    interaction_type: str = Field(description="Type of interaction. Must be one of: Meeting, Call, Email, Video")
    date: Optional[str] = Field(default=None, description="Date of interaction in YYYY-MM-DD format (defaults to current date)")
    time: Optional[str] = Field(default=None, description="Time of interaction in HH:MM format (defaults to current time)")
    topics_discussed: str = Field(description="Detailed summary of the topics discussed")
    observed_sentiment: str = Field(description="Sentiment observed. Must be one of: Positive, Neutral, Negative")
    attendees: Optional[str] = Field(default=None, description="Names of other attendees, comma separated")
    outcomes: Optional[str] = Field(default=None, description="Key outcomes or agreements")
    follow_up_actions: Optional[str] = Field(default=None, description="Next steps or follow-up tasks")
    products: Optional[List[str]] = Field(default=None, description="Names of products discussed (e.g., CardioFlow 10mg)")
    materials: Optional[List[str]] = Field(default=None, description="Names of materials shared (e.g., Cardiology Patient Guide)")
    samples: Optional[List[Dict[str, Any]]] = Field(default=None, description="List of samples distributed. Format: [{'name': 'CardioFlow 10mg Sample Pack', 'quantity': 2}]")

class EditInteractionInput(BaseModel):
    interaction_id: Optional[int] = Field(default=None, description="ID of the interaction to edit. If not provided, falls back to the current active interaction.")
    hcp_name: Optional[str] = Field(default=None, description="HCP name (used to search for the last interaction if ID is missing)")
    observed_sentiment: Optional[str] = Field(default=None, description="Updated observed sentiment (Positive, Neutral, Negative)")
    topics_discussed: Optional[str] = Field(default=None, description="Updated topics discussed")
    interaction_type: Optional[str] = Field(default=None, description="Updated interaction type (Meeting, Call, Email, Video)")
    date: Optional[str] = Field(default=None, description="Updated date in YYYY-MM-DD format")
    time: Optional[str] = Field(default=None, description="Updated time in HH:MM format")
    outcomes: Optional[str] = Field(default=None, description="Updated outcomes or agreements")
    follow_up_actions: Optional[str] = Field(default=None, description="Updated follow-up actions")

class GetHCPContextInput(BaseModel):
    hcp_name: str = Field(description="Name of the Healthcare Professional to retrieve history and context for")

class SearchInteractionsInput(BaseModel):
    query: Optional[str] = Field(default=None, description="Keyword query to search in topics, outcomes, or follow-ups")
    limit: Optional[int] = Field(default=5, description="Maximum number of search results to return")

class SuggestFollowUpInput(BaseModel):
    interaction_id: Optional[int] = Field(default=None, description="ID of the interaction to generate suggestions for. If missing, uses active interaction.")

class ManageSamplesInput(BaseModel):
    action: str = Field(description="Inventory action. Must be: list_samples, list_materials")

# API Requests & Responses
class ChatRequest(BaseModel):
    message: str
    current_interaction_id: Optional[int] = None

class ToolCallRecord(BaseModel):
    name: str
    args: Dict[str, Any]
    status: str  # "success" or "error"
    result: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    current_interaction_id: Optional[int] = None
    form_data: Optional[Dict[str, Any]] = None
    hcp_context: Optional[Dict[str, Any]] = None
    tool_calls: List[ToolCallRecord] = []

class HealthResponse(BaseModel):
    status: str
    database: str

class ManualCreateInteractionRequest(BaseModel):
    hcp_id: int
    interaction_type: str
    date: date
    time: str  # HH:MM format
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    observed_sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    products: List[int] = []
    materials: List[int] = []
    samples: List[Dict[str, Any]] = [] # [{'id': 1, 'quantity': 2}]

class ManualEditInteractionRequest(BaseModel):
    interaction_type: Optional[str] = None
    date: Optional[datetime.date] = None
    time: Optional[str] = None
    attendees: Optional[str] = None
    topics_discussed: Optional[str] = None
    observed_sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None
    products: Optional[List[int]] = None
    materials: Optional[List[int]] = None
    samples: Optional[List[Dict[str, Any]]] = None # [{'id': 1, 'quantity': 2}]

    @field_validator('date', mode='before')
    @classmethod
    def empty_date_to_none(cls, v):
        if v == "":
            return None
        return v

    @field_validator('time', mode='before')
    @classmethod
    def empty_time_to_none(cls, v):
        if v == "":
            return None
        return v

class HCPResponse(BaseModel):
    id: int
    name: str
    specialty: str
    clinic_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]

    class Config:
        from_attributes = True

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    therapeutic_area: str

    class Config:
        from_attributes = True

class MaterialResponse(BaseModel):
    id: int
    name: str
    type: str

    class Config:
        from_attributes = True

class SampleResponse(BaseModel):
    id: int
    name: str
    stock_quantity: int

    class Config:
        from_attributes = True

class MetadataResponse(BaseModel):
    hcps: List[HCPResponse]
    products: List[ProductResponse]
    materials: List[MaterialResponse]
    samples: List[SampleResponse]
