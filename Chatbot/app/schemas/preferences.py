from pydantic import BaseModel
from typing import List
from datetime import datetime


class UserPreference(BaseModel):
    session_token: str
    user_id: str | None = None

    budget_min: float | None = None
    budget_max: float | None = None
    preferred_brands: List[str] | None = None
    preferred_body_types: List[str] | None = None
    preferred_fuel_types: List[str] | None = None
    preferred_transmission: str | None = None
    preferred_cities: List[str] | None = None
    max_km_driven: int | None = None
    year_min: int | None = None
    year_max: int | None = None
    use_case: str | None = None

    is_seller: bool = False
    seller_car_brand: str | None = None
    seller_car_model: str | None = None
    seller_car_year: int | None = None
    seller_asking_price: float | None = None
    seller_intent: str | None = None

    intent_history: List[str] | None = None
    turn_count: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
