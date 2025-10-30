from datetime import datetime, timedelta
import random

FILE_PATH = "Anti-Finger.txt"

# กำหนดจำนวนวัน
num_days = 30

# ตั้งค่าเริ่มต้นวัน
start_date = datetime(2025, 10, 1, 8, 0, 0)

# รายการท่าฝึก
exercises = [
    "ท่าเหยียดมือตรงสําเร็จ!",
    "ท่าทำมือคล้ายตะขอสําเร็จ!",
    "ท่ากำมือสําเร็จ!",
    "ท่ากำมือแบบเหยียดปลายนิ้วสําเร็จ!",
    "ท่างอโคนนิ้วแต่เหยียดปลายนิ้วมือสําเร็จ!"
]

with open(FILE_PATH, "w", encoding="utf-8") as f:
    for day_offset in range(num_days):
        # วันปัจจุบัน
        day = start_date + timedelta(days=day_offset)
        
        # จำนวนเซ็ตต่อวัน (1-3 เซ็ต สุ่มได้ตามต้องการ)
        sets_today = random.choice([2, 3])  # ตัวอย่าง: สุ่มวันละ 2 หรือ 3 เซ็ต
        
        for set_index in range(sets_today):
            for rep_index in range(10):  # 10 ครั้ง = 1 เซ็ต
                # เลือกท่าออกกำลังกายแบบวน
                exercise = exercises[rep_index % len(exercises)]
                
                # เวลาสมมติ เพิ่ม 7 วินาทีต่อครั้ง (เหมือนตัวอย่าง)
                time_offset = timedelta(seconds=7 * (rep_index + set_index * 10))
                timestamp = day + time_offset
                
                line = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] เซ็ตที่ {set_index} ครั้งที่ {rep_index} : {exercise}\n"
                f.write(line)
        
        # เพิ่มบรรทัดว่างระหว่างวัน
        f.write("\n")

print(f"สร้างไฟล์ {FILE_PATH} เสร็จเรียบร้อย!")
