from pydantic import BaseModel
from typing import List, Optional

class CartItem(BaseModel):
    name: str
    quantity: int
    price: float
    category: Optional[str] = "main"

class RecommendationRequest(BaseModel):
    items: List[CartItem]

class RecommendedAddOn(BaseModel):
    name: str
    reason: str
    estimated_price: Optional[float] = None

class RecommendationResponse(BaseModel):
    recommendations: List[RecommendedAddOn]
