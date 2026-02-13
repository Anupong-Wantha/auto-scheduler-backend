from ortools.sat.python import cp_model
from app.services.scheduler.constraints import ConstraintBuilder
from app.services.scheduler.validator import ScheduleValidator

class AutoSchedulerService:
    def __init__(self, data):
        """
        data structure matches the one returned by repository.fetch_all_initial_data()
        """
        self.data = data
        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
        self.shifts = {}  # เก็บตัวแปร Decision Variables

        # Helper Maps เพื่อให้ทำงานเร็วขึ้น
        self.subject_credits = {s['subject_id']: (s['theory'] + s['practice']) for s in self.data['subjects']}
        self.subject_names = {s['subject_id']: s['subject_name'] for s in self.data['subjects']}

    def solve(self):
        print("\n=== Starting Auto Scheduler (Optimized for Morning) ===")
        
        # 1. ตรวจสอบความเป็นไปได้ของข้อมูล (Advanced Diagnostics)
        diag_result = self._diagnose_data()
        if not diag_result['is_valid']:
            return {
                "status": "failed",
                "message": f"Data Diagnostics Failed: {diag_result['message']}",
                "data": []
            }

        print("Step 1: Creating Variables...")
        self._create_variables()
        
        if not self.shifts:
             return {
                "status": "failed",
                "message": "No variables created. Check 'teach' table assignments.",
                "data": []
            }

        print(f"Step 2: Applying Constraints... ({len(self.shifts)} variables)")
        builder = ConstraintBuilder(self.model, self.shifts, self.data)
        builder.apply_all_constraints()

        # Constraints หลักสูตร (ต้องเรียนให้ครบตามหน่วยกิต)
        self._add_curriculum_constraints()

        # =========================================================
        # [NEW] Step 2.5: Objective Function (Morning Preference)
        # =========================================================
        print("Step 2.5: Setting Objective to prefer morning classes...")
        objective_terms = []
        for key, var in self.shifts.items():
            # key = (group, subject, teacher, room, day, period)
            period = key[5]
            
            # ยิ่งคาบเยอะ ยิ่ง Cost เยอะ -> AI จะพยายามเลี่ยง
            # ใช้ period * period เพื่อให้แรงดึงดูดช่วงเช้าแรงขึ้น
            # คาบ 1 cost = 1
            # คาบ 10 cost = 100
            # คาบ 12 cost = 144
            cost = period * period 
            
            objective_terms.append(var * cost)

        # สั่งให้ AI หาทางออกที่ Cost ต่ำที่สุด (Minimize)
        if objective_terms:
            self.model.Minimize(sum(objective_terms))
        # =========================================================

        print("Step 3: Solving...")
        # ตั้งเวลาคิดสูงสุด 60 วินาที
        self.solver.parameters.max_time_in_seconds = 60.0 
        status = self.solver.Solve(self.model)

        print(f"Step 4: Result Status: {self.solver.StatusName(status)}")
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            raw_schedule = self._extract_solution()
            return {
                "status": "success", 
                "message": f"Schedule found ({self.solver.StatusName(status)})", 
                "data": raw_schedule
            }
        else:
            return {
                "status": "failed", 
                "message": "Infeasible: No solution found. Check constraints or teacher workload.",
                "data": []
            }

    def _diagnose_data(self):
        """
        ตรวจสอบความเป็นไปได้ของข้อมูล: เวลาเรียนเด็ก / ภาระครู / ภาระห้องเรียน
        """
        print("--- Running Advanced Diagnostics ---")
        is_valid = True
        
        # 1. คำนวณ Slot
        total_slots = len(self.data['timeslots'])
        blocked_slots = 5 # พักเที่ยง
        available_slots = total_slots - blocked_slots
        print(f"[Diag] Max Slots Available: {available_slots}")

        # Helper Maps
        subj_teacher_map = {}
        for t in self.data['teach_map']:
            if t['subject_id'] not in subj_teacher_map:
                subj_teacher_map[t['subject_id']] = t['teacher_id']

        # Fix Subject/Room check (Example: IOT)
        iot_subject_name = "การอินเทอร์เฟส"
        iot_room_match = [r['room_id'] for r in self.data['rooms'] if 'IOT' in (r['room_name'] or "")]
        iot_room_id = iot_room_match[0] if iot_room_match else 'R6201'

        group_load = {}
        teacher_load = {}
        
        for reg in self.data['register_map']:
            g_id = reg['group_id']
            s_id = reg['subject_id']
            hours = self.subject_credits.get(s_id, 0)

            # Check Load
            group_load[g_id] = group_load.get(g_id, 0) + hours
            
            t_id = subj_teacher_map.get(s_id)
            if t_id:
                teacher_load[t_id] = teacher_load.get(t_id, 0) + hours

        # Report Errors
        for g, load in group_load.items():
            if load > available_slots:
                print(f"❌ IMPOSSIBLE Group: {g} needs {load} hours (Max {available_slots})")
                is_valid = False

        for t, load in teacher_load.items():
            if load > available_slots:
                print(f"❌ IMPOSSIBLE Teacher: {t} needs {load} hours (Max {available_slots})")
                is_valid = False
            elif load > available_slots * 0.9:
                print(f"⚠️ WARNING Teacher: {t} is very busy ({load}/{available_slots})")

        if is_valid:
            print("✅ Diagnostics Passed.")
        else:
            print("❌ Diagnostics Failed.")
            
        return {"is_valid": is_valid, "message": "Check logs"}

    def _create_variables(self):
        teacher_map = {}
        for t in self.data['teach_map']:
            if t['subject_id'] not in teacher_map: teacher_map[t['subject_id']] = []
            teacher_map[t['subject_id']].append(t['teacher_id'])

        for reg in self.data['register_map']:
            group_id = reg['group_id']
            subject_id = reg['subject_id']
            possible_teachers = teacher_map.get(subject_id, [])
            
            if not possible_teachers:
                continue

            for room in self.data['rooms']:
                for timeslot in self.data['timeslots']: 
                    day = timeslot['day']
                    period = timeslot['period']
                    for teacher_id in possible_teachers:
                        key = (group_id, subject_id, teacher_id, room['room_id'], day, period)
                        self.shifts[key] = self.model.NewBoolVar(f"s_{group_id}_{subject_id}_{day}_{period}")

    def _add_curriculum_constraints(self):
        registry_vars = {} 
        for key, var in self.shifts.items():
            g, s = key[0], key[1]
            if (g, s) not in registry_vars: registry_vars[(g, s)] = []
            registry_vars[(g, s)].append(var)

        for reg in self.data['register_map']:
            g, s = reg['group_id'], reg['subject_id']
            vars_list = registry_vars.get((g, s), [])
            required = self.subject_credits.get(s, 0)
            if not vars_list: continue 
            if required > 0:
                self.model.Add(sum(vars_list) == required)

    def _extract_solution(self):
        schedule = []
        for key, var in self.shifts.items():
            if self.solver.Value(var) == 1:
                schedule.append({
                    "group": key[0],
                    "subject": key[1],
                    "teacher": key[2],
                    "room": key[3],
                    "day": key[4],
                    "period": key[5]
                })
        return schedule