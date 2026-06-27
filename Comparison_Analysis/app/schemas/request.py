from pydantic import BaseModel, field_validator
from typing import Literal


class CompareRequest(BaseModel):
    ad_ids: list[str]
    language: Literal["en", "ar"] = "en"

    @field_validator("ad_ids")
    @classmethod
    def validate_ad_ids(cls, v):
        if len(v) < 2 or len(v) > 3:
            raise ValueError("Must provide 2 or 3 ad_ids")
        if len(v) != len(set(v)):
            raise ValueError("Duplicate ad_ids are not allowed")
        return v
