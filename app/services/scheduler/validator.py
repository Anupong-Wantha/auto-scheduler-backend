class ScheduleValidator:
    def __init__(self, schedule_list: list, data: dict):
        """
        :param schedule_list: List ของ dict ผลลัพธ์ 
               [{'group': 'G1', 'subject': 'S1', 'teacher': 'T1', 'room': 'R1', 'day': 'Mon', 'period': 1}, ...]
        :param data: ข้อมูล Master Data
        """
        self.schedule = schedule_list
        self.data = data
        self.errors = []

    def validate(self):
        self.errors = []
        self._v_lunch_break()
        self._v_teacher_conflict()
        self._v_room_conflict()
        self._v_daily_limit()
        self._v_iot_lab()
        self._v_leader_meeting()
        self._v_evening_theory()
        self._v_subject_counts()
        return {
            "is_valid": len(self.errors) == 0,
            "errors": self.errors
        }

    def _v_lunch_break(self):
        # 2. No classes in Period 5
        for s in self.schedule:
            if s['period'] == 5:
                self.errors.append(f"Lunch Break Violation: {s}")

    def _v_teacher_conflict(self):
        # 6. Teacher cannot teach >1 class simultaneously
        # Key: (Teacher, Day, Period)
        usage = {}
        for s in self.schedule:
            key = (s['teacher'], s['day'], s['period'])
            if key in usage:
                self.errors.append(f"Teacher Conflict: {s['teacher']} at {s['day']} p{s['period']}")
            usage[key] = True

    def _v_room_conflict(self):
        # 7. Room cannot host >1 class simultaneously
        usage = {}
        for s in self.schedule:
            key = (s['room'], s['day'], s['period'])
            if key in usage:
                self.errors.append(f"Room Conflict: {s['room']} at {s['day']} p{s['period']}")
            usage[key] = True

    def _v_daily_limit(self):
        # 5. Max 10 periods per day per group
        counts = {} # (Group, Day) -> count
        for s in self.schedule:
            key = (s['group'], s['day'])
            counts[key] = counts.get(key, 0) + 1
        
        for key, count in counts.items():
            if count > 10:
                self.errors.append(f"Daily Limit Exceeded: Group {key[0]} on {key[1]} has {count} periods")

    def _v_iot_lab(self):
        # 14. Subject 'IOT' must be in 'R6201'
        for s in self.schedule:
            if s['subject'] == 'IOT' and s['room'] != 'R6201':
                self.errors.append(f"IOT Lab Violation: IOT is in {s['room']}")

    def _v_leader_meeting(self):
        # 10. Teachers 'Leader' free Tue Period 8
        leaders = {t['teacher_id'] for t in self.data['teachers'] if t.get('role') == 'Leader'}
        for s in self.schedule:
            if s['teacher'] in leaders and s['day'] == 'Tue' and s['period'] == 8:
                self.errors.append(f"Leader Meeting Violation: {s['teacher']} is busy")

    def _v_evening_theory(self):
        # 15. Avoid Theory after Period 9
        subjects = {subj['subject_id']: subj for subj in self.data['subjects']}
        for s in self.schedule:
            subj = subjects.get(s['subject'])
            if subj and subj['theory'] > 0 and s['period'] > 9:
                self.errors.append(f"Evening Theory: {s['subject']} scheduled at p{s['period']}")

    def _v_subject_counts(self):
        # 1, 3, 4. Check Total Periods match Theory + Practice
        # ต้อง Group ตาม (Group, Subject) แล้วนับจำนวนคาบเทียบกับ Data
        actual_counts = {} # (Group, Subject) -> count
        for s in self.schedule:
            key = (s['group'], s['subject'])
            actual_counts[key] = actual_counts.get(key, 0) + 1
            
        # สมมติว่า Register Table อยู่ใน self.data['register_map']
        # และ Subject Info อยู่ใน self.data['subjects']
        subject_info = {subj['subject_id']: (subj['theory'] + subj['practice']) for subj in self.data['subjects']}
        
        for reg in self.data['register_map']:
            group = reg['group_id']
            subject = reg['subject_id']
            required_hours = subject_info.get(subject, 0)
            
            scheduled_hours = actual_counts.get((group, subject), 0)
            
            if scheduled_hours != required_hours:
                self.errors.append(f"Period Count Mismatch: Group {group}, Subject {subject}. Expected {required_hours}, Got {scheduled_hours}")