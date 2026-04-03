from typing import Optional

from pydantic import BaseModel, ConfigDict


class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None


class AgentCreate(AgentBase):
    pass


class AgentRead(AgentBase):
    id: int
    client_id: str
    client_secret: str
    is_frozen: bool

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
