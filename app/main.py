import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import api_router

app = FastAPI(title="Auto Scheduler API")

# ดึง URL หน้าบ้านจาก Environment Variable ถ้าไม่มีให้ใช้ localhost
frontend_url = os.getenv("https://schedule-app-1-a8bq-git-main-anupong-wanthas-projects.vercel.app/", "http://localhost:3000")

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    frontend_url, # URL จริงจาก Vercel หรือ Netlify
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "Auto Scheduler AI Engine is running",
        "version": "1.0.0"
    }