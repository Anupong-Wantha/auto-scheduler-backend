from app.db.supabase import supabase_client

class ScheduleRepository:
    def __init__(self):
        self.client = supabase_client

    def fetch_all_initial_data(self):
        """ดึงข้อมูลดิบทั้งหมดที่จำเป็นสำหรับการคำนวณ"""
        try:
            # ดึงข้อมูลแบบ Parallel หรือ Sequential ก็ได้
            teachers = self.client.table("teacher").select("*").execute()
            subjects = self.client.table("subject").select("*").execute()
            rooms = self.client.table("room").select("*").execute()
            groups = self.client.table("student_group").select("*").execute()
            timeslots = self.client.table("timeslot").select("*").execute()
            
            # Relations
            teach_rel = self.client.table("teach").select("*").execute()
            register_rel = self.client.table("register").select("*").execute()

            return {
                "teachers": teachers.data,
                "subjects": subjects.data,
                "rooms": rooms.data,
                "groups": groups.data,
                "timeslots": timeslots.data,
                "teach_map": teach_rel.data,
                "register_map": register_rel.data
            }
        except Exception as e:
            print(f"DB Error: {e}")
            raise e