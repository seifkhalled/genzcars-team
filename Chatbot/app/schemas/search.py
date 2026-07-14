from typing import Optional
from pydantic import BaseModel, field_validator


class LLMExtractedFilters(BaseModel):
    """Filters the query-builder LLM is asked to extract from the user message.

    NOTE: the `excluded_*` / `year_*` fields are NOT produced by the LLM — they
    are sourced from the user's accumulated preferences (see search_node._prefs_to_filters_dict)
    and merged in separately. The LLM only ever populates the inclusion filters below.
    """

    search_query: str
    brand: Optional[str] = None
    brands: Optional[list[str]] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    city: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    body_types: Optional[list[str]] = None
    excluded_body_types: Optional[list[str]] = None
    excluded_brands: Optional[list[str]] = None
    excluded_models: Optional[list[str]] = None
    year_min: Optional[int] = None
    year_max: Optional[int] = None

    @field_validator("brand")
    @classmethod
    def prevent_both_brand_and_brands(cls, v, info):
        brands = info.data.get("brands")
        if v and brands:
            raise ValueError("Use either 'brand' (single) or 'brands' (list), not both")
        return v


class CarAd(BaseModel):
    id: str
    brand: str = ""
    model: str = ""
    year: int = 0
    price: float = 0.0
    condition: str = ""
    km_driven: int = 0
    body_type: str = ""
    transmission: str = ""
    fuel_type: str = ""
    city: str = ""
    cover_image_url: str = ""
    images: list[dict] = []
    score: float = 0.0
