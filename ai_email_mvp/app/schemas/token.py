from pydantic import BaseModel

class TokenRequest(BaseModel):
    access_token: str
    extension_id: str

class Token(BaseModel):
    access_token: str
    token_type: str
