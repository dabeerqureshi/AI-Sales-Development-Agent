from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CampaignBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Campaign descriptive title")
    industry: str = Field(..., min_length=2, max_length=100, description="Target industry (e.g., Dentist)")
    country: str = Field(default="United States", max_length=100)
    region: Optional[str] = Field(None, max_length=100, description="State or province (e.g., Texas)")
    city: str = Field(..., min_length=2, max_length=100, description="Target city (e.g., Austin)")
    max_leads: int = Field(default=50, ge=1, le=500, description="Maximum leads to discover")
    website_required: bool = Field(default=False, description="Filter: only keep leads with official websites")
    phone_required: bool = Field(default=False, description="Filter: only keep leads with phone numbers")


class CampaignCreate(CampaignBase):
    pass


class CampaignResponse(CampaignBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    lead_count: int = 0
    created_at: datetime
    updated_at: datetime
