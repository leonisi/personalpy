from fastapi import Body


from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from models import Transaction, TransactionCreate, UserCreate, UserLogin, User
from database import get_db_connection, init_db
from typing import List
from passlib.context import CryptContext
import uuid
import os
from dotenv import load_dotenv


load_dotenv()
DB_PATH = os.getenv("DATABASE_URL", "finance.db")
print("Using database file:", DB_PATH)

app = FastAPI()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(user_id):
    # Generate a random token and store it in the DB for the user
    token = str(uuid.uuid4())
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET token = ? WHERE id = ?", (token, user_id))
    conn.commit()
    print(f"Set token for user {user_id}: {token}")
    conn.close()
    return token

def get_user_by_username(username):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()
    return row

def get_user_by_token(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE token = ?", (token,))
    row = cursor.fetchone()
    conn.close()
    return row

def authenticate_user(username, password):
    user = get_user_by_username(username)
    if not user:
        return None
    if not verify_password(password, user[2]):
        return None
    return user

def get_current_user(token: str = Depends(oauth2_scheme)):
    print("Received token:", token)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = get_user_by_token(token)
    print("User found:", user)
    if user is None:
        raise credentials_exception
    return user
@app.post("/register", response_model=User)
def register(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    password_hash = get_password_hash(user.password)
    try:
        cursor.execute("INSERT INTO users (username, password_hash, token) VALUES (?, ?, ?)", (user.username, password_hash, None))
        conn.commit()
        user_id = cursor.lastrowid
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
    conn.close()
    return User(id=user_id, username=user.username)

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(user[0])
    return {"access_token": access_token, "token_type": "bearer"}

@app.on_event("startup")
def startup():
    init_db()


@app.post("/transactions/", response_model=Transaction)
def add_transaction(tx: TransactionCreate, user=Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO transactions (user_id, date, description, amount, category) VALUES (?, ?, ?, ?, ?)",
        (user[0], tx.date, tx.description, tx.amount, tx.category)
    )
    conn.commit()
    tx_id = cursor.lastrowid
    conn.close()
    return Transaction(id=tx_id, user_id=user[0], **tx.dict())


@app.get("/transactions/", response_model=List[Transaction])
def list_transactions(user=Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM transactions WHERE user_id = ?", (user[0],))
    rows = cursor.fetchall()
    conn.close()
    return [Transaction(**dict(row)) for row in rows]


@app.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: str, user=Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, user[0]))
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"detail": "Transaction deleted"}

# Update transaction endpoint
@app.put("/transactions/{tx_id}", response_model=Transaction)
def update_transaction(tx_id: int, tx: TransactionCreate = Body(...), user=Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE transactions SET date = ?, description = ?, amount = ?, category = ? WHERE id = ? AND user_id = ?",
        (tx.date, tx.description, tx.amount, tx.category, tx_id, user[0])
    )
    conn.commit()
    affected = cursor.rowcount
    conn.close()
    if affected == 0:
        raise HTTPException(status_code=404, detail="Transaction not found or not owned by user")
    return Transaction(id=tx_id, user_id=user[0], **tx.dict())
