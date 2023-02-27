# shortener_app/schemas.py

from pydantic import BaseModel

class URLBase(BaseModel):
    url: str
