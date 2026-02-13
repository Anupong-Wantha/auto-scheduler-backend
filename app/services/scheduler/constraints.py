from ortools.sat.python import cp_model

class ConstraintBuilder:
    def __init__(self, model: cp_model.CpModel, shift_vars: dict, data: dict):
        self.model = model
        self.shifts = shift_vars
        self.data = data
        
        # Helper Lookup Maps
        self.subject_info = {s['subject_id']: s for s in self.data['subjects']}
        self.room_info = {r['room_id']: r for r in self.data['rooms']}
        self.teacher_info = {t['teacher_id']: t for t in self.data['teachers']}

    def apply_all_constraints(self):
        print("--- Applying 13 Constraints with Room Data ---")
        
        # 1-4. จัดการใน solver.py (หน่วยกิต/การลงทะเบียน)
        
        # 2. Lunch Break: คาบ 5 ห้ามมีเรียน
        self._c_lunch_break()
        
        # 5. Daily Limit: ไม่เกิน 10 คาบ/วัน
        self._c_daily_limit()
        
        # 6. Teacher Conflict: ครูห้ามสอนซ้อน
        self._c_teacher_conflict()
        
        # 7. Room Conflict: ห้องห้ามใช้ซ้อน
        self._c_room_conflict()
        
        # 9. Room Type Matching: ทฤษฎีใช้ห้อง Theory / ปฏิบัติใช้ห้อง Lab
        self._c_room_type_matching_v2()
        
        # 10. Leader Meeting: 'Leader' ว่าง อังคาร คาบ 8
        self._c_leader_meeting()
        
        # 12. Activity: พุธ คาบ 8-9 (ล็อกรหัสวิชากิจกรรม)
        self._c_activity_time()
        
        # 13. Joint Classes: รหัส 2xxxx/3xxxx เรียนรวม
        # self._c_joint_classes()

        # Extra: เงื่อนไขเฉพาะ
        self._c_evening_theory_limit() # หลีกเลี่ยงทฤษฎีหลังคาบ 9
        self._c_iot_lab_exclusive()    # วิชา IOT ต้องลงห้อง IOT Lab (R6201) เท่านั้น

    # ---------------------------------------------------------
    # 9. Room Type Matching (อัปเดตตามข้อมูลใหม่)
    # ---------------------------------------------------------
    def _c_room_type_matching_v2(self):
        """ 
        - วิชาทฤษฎีล้วน (Theory > 0, Practice == 0) -> ต้องใช้ห้องประเภท 'Theory'
        - วิชาที่มีปฏิบัติ (Practice > 0) -> ต้องใช้ห้องประเภทที่เป็น 'Lab' ต่างๆ
        """
        for key, var in self.shifts.items():
            subj_id, room_id = key[1], key[3]
            subj = self.subject_info.get(subj_id)
            room = self.room_info.get(room_id)
            
            if subj and room:
                room_type = room.get('room_type', '')
                
                # กรณีวิชาทฤษฎีล้วน
                if subj.get('theory', 0) > 0 and subj.get('practice', 0) == 0:
                    if room_type != 'Theory':
                        self.model.Add(var == 0)
                
                # กรณีวิชาที่มีปฏิบัติ
                elif subj.get('practice', 0) > 0:
                    if room_type == 'Theory':
                        # วิชาปฏิบัติห้ามใช้ห้องทฤษฎี (ยกเว้นตารางแน่นจริงๆ อาจต้องผ่อนปรน)
                        self.model.Add(var == 0)

    # ---------------------------------------------------------
    # วิชา IOT -> เฉพาะห้อง R6201 (IOT Lab)
    # ---------------------------------------------------------
    def _c_iot_lab_exclusive(self):
        target_subject_keyword = "การอินเทอร์เฟส"
        target_room_id = "R6201" # ตามตาราง room ที่ส่งมา

        for key, var in self.shifts.items():
            subj_id, room_id = key[1], key[3]
            subj = self.subject_info.get(subj_id)
            
            if subj and target_subject_keyword in subj['subject_name']:
                if room_id != target_room_id:
                    self.model.Add(var == 0)

    # ---------------------------------------------------------
    # 13. Joint Classes: เรียนรวมรหัส 2/3
    # ---------------------------------------------------------
    def _c_joint_classes(self):
        # รวมกลุ่มตัวแปรที่ควรจะเรียนพร้อมกัน
        joint_map = {}
        for key, var in self.shifts.items():
            group, subj, teacher, room, day, period = key
            if subj.startswith('2') or subj.startswith('3'):
                # คีย์มัดรวม: (วิชา, ครู, ห้อง, วัน, คาบ)
                k = (subj, teacher, room, day, period)
                if k not in joint_map: joint_map[k] = []
                joint_map[k].append(var)
        
        for vars_list in joint_map.values():
            if len(vars_list) > 1:
                # บังคับให้ทุกกลุ่มในลิสต์มีสถานะเดียวกัน (ถ้ากลุ่มหนึ่งเรียน อีกกลุ่มต้องเรียนด้วย)
                for i in range(len(vars_list) - 1):
                    self.model.Add(vars_list[i] == vars_list[i+1])

    # ---------------------------------------------------------
    # Basic & Others
    # ---------------------------------------------------------
    def _c_lunch_break(self):
        for key, var in self.shifts.items():
            if key[5] == 5: self.model.Add(var == 0)

    def _c_daily_limit(self):
        group_day_vars = {}
        for key, var in self.shifts.items():
            g, d = key[0], key[4]
            if (g, d) not in group_day_vars: group_day_vars[(g, d)] = []
            group_day_vars[(g, d)].append(var)
        for vars in group_day_vars.values():
            self.model.Add(sum(vars) <= 10)

    def _c_teacher_conflict(self):
        teacher_vars = {}
        for key, var in self.shifts.items():
            t, d, p = key[2], key[4], key[5]
            if (t, d, p) not in teacher_vars: teacher_vars[(t, d, p)] = []
            teacher_vars[(t, d, p)].append(var)
        for vars in teacher_vars.values():
            self.model.Add(sum(vars) <= 1)

    def _c_room_conflict(self):
        room_vars = {}
        for key, var in self.shifts.items():
            r, d, p = key[3], key[4], key[5]
            if (r, d, p) not in room_vars: room_vars[(r, d, p)] = []
            room_vars[(r, d, p)].append(var)
        for vars in room_vars.values():
            self.model.Add(sum(vars) <= 1)

    def _c_leader_meeting(self):
        for key, var in self.shifts.items():
            t_id, day, period = key[2], key[4], key[5]
            teacher = self.teacher_info.get(t_id)
            if teacher and teacher.get('role') == 'Leader':
                if day == 'Tue' and period == 8: self.model.Add(var == 0)

    def _c_activity_time(self):
        ACTIVITY_CODE = "20000-2001" 
        for key, var in self.shifts.items():
            subj, day, period = key[1], key[4], key[5]
            if day == 'Wed' and period in [8, 9]:
                if subj != ACTIVITY_CODE: self.model.Add(var == 0)
            elif subj == ACTIVITY_CODE:
                self.model.Add(var == 0)

    def _c_evening_theory_limit(self):
        for key, var in self.shifts.items():
            subj_id, period = key[1], key[5]
            subj = self.subject_info.get(subj_id)
            if subj and subj.get('theory', 0) > 0 and period > 9:
                self.model.Add(var == 0)