# AI-Powered Anti-Trigger Fingers With OpenCV

![Logo](pictures/logo.png)

**AI-Powered Anti-Trigger Fingers** เป็นแอปพลิเคชันสำหรับฝึกท่ามือ ป้องกันนิ้วล็อค (Trigger Fingers) ด้วย **คอมพิวเตอร์วิชัน** แบบเรียลไทม์ พร้อม **จับเวลา, แสดงภาพตัวอย่างท่า, และเสียงประกอบ**  

---

## 🌟 คุณสมบัติหลัก (Features)

- 🖐 ตรวจจับ **ท่ามือแบบเรียลไทม์** ผ่านเว็บแคม
- 🤖 ใช้ **MediaPipe Hands** วิเคราะห์โครงสร้างมือและมุมของนิ้ว
- 🎨 แสดงภาพตัวอย่างท่ามือ (EX Pose) พร้อมข้อความคำอธิบาย
- ⏱ จับเวลาแต่ละท่า พร้อมวงกลมโปรเกรสแบบเรียลไทม์
- 🔊 มีเสียงประกอบ MP3 สำหรับแต่ละท่า
- 📊 บันทึกประวัติการฝึกในไฟล์ `Anti-Finger.txt`
- 📄 หน้า **รายงานย้อนหลัง** แสดงเซ็ตและจำนวนครั้งที่สำเร็จ
- 🖥 UI สวยงามด้วย **CustomTkinter**

---

## 🎬 ตัวอย่าง UI

**หน้าหลัก:**
![Main UI](pictures/main.png)

**รายงานย้อนหลัง:**
![History Page](pictures/log.png)
---

## 🚀 วิธีใช้งาน (Usage)

1. เปิดโปรแกรมด้วย:
   ```bash
   python main.py
   ```
   
2.กดปุ่ม เริ่มต้น เพื่อเริ่มฝึกท่า

3.ทำท่ามือให้ตรงกับภาพตัวอย่าง

4.ระบบจะจับเวลาและบันทึกผลเมื่อทำสำเร็จ

5.ตรวจสอบ รายงานย้อนหลัง ผ่านปุ่ม รายงาน

⚙️ การติดตั้ง (Installation)

1.ติดตั้ง Python 3.11+ (Recommend 3.11.9)

2.สร้าง Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows
```

ติดตั้ง dependencies:
```bash
pip install opencv-python mediapipe Pillow customtkinter pygame
```

📁 โครงสร้างโปรเจกต์ (Project Structure)
```bash
AntiTriggerFingers/
│
├─ main.py                 # ไฟล์หลักรันแอป
├─ Anti-Finger.txt         # บันทึกประวัติการฝึก
├─ Voices/                 # โฟลเดอร์ไฟล์เสียง
│   ├─ 001.mp3
│   ├─ 002.mp3
│   └─ ...
└─ pictures/
    ├─ logo.png
    └─ EX_POSE/
        ├─ pose1.png
        ├─ pose2.png
        └─ pose5.png
```

📊 การทำงานของระบบ

1.ระบบเปิด เว็บแคม และประมวลผลมือผ่าน MediaPipe

2.ตรวจสอบมุมของนิ้วแต่ละนิ้ว เปรียบเทียบกับช่วงของท่าที่กำหนด

3.ถ้าท่าตรงกับเงื่อนไข จะเริ่ม จับเวลา

4.ครบเวลา → บันทึกผลลงไฟล์ Anti-Finger.txt และเล่นเสียงประกอบ

5.อัปเดต UI Timer, EX Pose, และ หน้า History


🔔 License

-OPEN SOURCE 

👨‍💻 Author

Tayakorn000,Achidesu

GitHub: https://github.com/tayakorn000

Email: tayakornwet@gmail.com

