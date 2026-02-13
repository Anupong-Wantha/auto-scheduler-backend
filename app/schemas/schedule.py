from pydantic import BaseModel
from typing import List, Optional

# --- Base Models for DB ---
class Teacher(BaseModel):
    teacher_id: str
    teacher_name: str
    role: Optional[str] = None

class Subject(BaseModel):
    subject_id: str
    subject_name: str
    theory: int
    practice: int
    credit: int

class Room(BaseModel):
    room_id: str
    room_name: Optional[str]
    room_type: Optional[str]

# --- Response Model สำหรับ API ---
class ScheduleResult(BaseModel):
    status: str
    message: str
    schedule_data: Optional[List[dict]] = None # เก็บผลลัพธ์ตารางที่จัดเสร็จแล้ว