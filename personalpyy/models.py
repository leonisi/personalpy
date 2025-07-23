from pydantic import BaseModel
from typing import Optional

from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(BaseModel):
    id: int
    username: str

class Transaction(BaseModel):
    id: int
    user_id: int
    date: str  # ISO format: YYYY-MM-DD
    description: Optional[str] = None
    amount: float
    category: Optional[str] = None

class TransactionCreate(BaseModel):
    date: str
    description: Optional[str] = None
    amount: float
    category: Optional[str] = None
