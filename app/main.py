from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router

app = FastAPI(title="Auto Scheduler API")

# --- เพิ่มส่วนนี้เข้าไป ---
origins = [
    "http://localhost:3000",    # URL ของ Next.js
    "http://127.0.0.1:3000",
    # เพิ่ม URL อื่นๆ ที่ต้องการให้เข้าถึงได้ที่นี่
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # อนุญาตเฉพาะ Next.js
    allow_credentials=True,
    allow_methods=["*"],               # อนุญาตทุก Method (GET, POST, OPTIONS, ฯลฯ)
    allow_headers=["*"],               # อนุญาตทุก Header
)
# -----------------------

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Auto Scheduler API"}