from fastapi import APIRouter, HTTPException, Depends, Query
from app.schemas.schedule import ScheduleResult
from app.db.repository import ScheduleRepository
from app.services.scheduler.solver import AutoSchedulerService

router = APIRouter()

@router.post("/generate", response_model=ScheduleResult)
def generate_schedule(save: bool = Query(False, description="Save result to database if successful")):
    try:
        # 1. ดึงข้อมูล
        repo = ScheduleRepository()
        raw_data = repo.fetch_all_initial_data()

        # 2. คำนวณ
        scheduler_service = AutoSchedulerService(raw_data)
        result = scheduler_service.solve()

        # [แก้ไข] เช็คสถานะก่อน ถ้าไม่ success ให้ return JSON บอกสาเหตุ (ไม่ raise 500)
        if result.get("status") != "success":
            return ScheduleResult(
                status=result.get("status"),
                message=f"Generation Failed: {result.get('message')}",
                schedule_data=[]
            )

        # 3. บันทึก (ถ้าสำเร็จและ user สั่ง save)
        if save and result.get("status") == "success":
            repo.save_schedule_bulk(result.get("data"))

        return ScheduleResult(
            status="success",
            message=result.get("message"),
            schedule_data=result.get("data")
        )

    except Exception as e:
        # อันนี้เผื่อ Error ที่เราคาดไม่ถึงจริงๆ
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))