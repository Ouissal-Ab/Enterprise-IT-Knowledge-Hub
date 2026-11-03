import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str = Field(..., min_length=8, description="Le mot de passe doit contenir au moins 8 caractères, une majuscule et un chiffre.")
    role: Literal["admin", "user"] = "user"

    @field_validator("email")
    @classmethod
    def validate_corporate_email(cls, value: str):
        pattern = r"^[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+@entreprise\.com$"
        if not re.match(pattern, value):
            raise ValueError(
                "Format d'e-mail incorrect. Il doit être sous la forme : prenom.nom@entreprise.com"
            )
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str):
        if not re.search(r"[A-Z]", value):
            raise ValueError("Le mot de passe doit contenir au moins une lettre majuscule.")
        if not re.search(r"[a-z]", value):
            raise ValueError("Le mot de passe doit contenir au moins une lettre minuscule.")
        if not re.search(r"\d", value):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
        return value
class UserUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=2, max_length=100)
    last_name: str | None = Field(None, min_length=2, max_length=100)
    email: str | None = None

    @field_validator("email")
    @classmethod
    def validate_corporate_email(cls, value: str | None):
        if value is None:
            return value
        pattern = r"^[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+@entreprise\.com$"
        if not re.match(pattern, value):
            raise ValueError(
                "Format d'e-mail incorrect. Il doit être sous la forme : prenom.nom@entreprise.com"
            )
        return value.lower()