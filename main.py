# ============================================================
#  🖐️ AI-Powered Anti-Trigger Fingers
#  Developed by : Tayakorn000 & Achidesu
#  Purpose      : Real-time hand-pose trainer to help prevent
#                 trigger finger (นิ้วล็อค) by guiding users
#                 through a set of finger exercises.
#
#  Highlights:
#    - Real-time camera preview (OpenCV -> PIL -> CustomTkinter)
#    - Hand landmarks & simple angle-based pose matching (MediaPipe)
#    - Progress timer visualization + animated arc
#    - Audio feedback (pygame) and history logging
#    - Organized UI: main page + history page
# ============================================================

# ==== Library Imports =======================================
from logging import root
from PIL import Image, ImageTk           # Image processing + Tkinter bridge
import customtkinter as ctk              # Modern Tkinter look-and-feel
import cv2                               # OpenCV for camera I/O and image ops
import mediapipe as mp                   # MediaPipe Hands: landmark detector
import pygame                            # For playing short sound cues
import time, threading                   # Threading for background loops, time helpers
from datetime import datetime,timedelta           # Timestamps for logging
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from collections import defaultdict
import sys,os
import tkinter as tk
from tkinter import ttk
# ============================================================


# --- Main Application Class ---
class AntiTriggerFingersApp(ctk.CTk):
    """
    Main application window.

    Responsibilities:
      - Build and manage the UI (CustomTkinter)
      - Run a background MediaPipe thread to detect hands
      - Run a periodic sensor loop that uses detection results to
        decrement a pose timer, trigger success events, and log history
      - Play short sound cues via pygame
      - Handle app lifecycle (start/stop/close)
    """

    def __init__(self):
        # --------------------
        # Window / base setup
        # --------------------
        super().__init__()
        self.title("AI-Powered Anti-trigger Fingers")
        self.attributes("-fullscreen", True)
        self.geometry("1920x1080+0+0")
        self.overrideredirect(True)       
        self.bind("<Escape>", lambda e: self.on_close())
        self.resizable(False, False)
        self.configure(fg_color="#FFFFFF")

        # --------------------
        # State variables
        # --------------------
        # These hold runtime state across UI and detection loops.
        self.key_held = False
        self.time_max = 5                            # seconds required per pose
        self.time_current = self.time_max            # remaining seconds for current pose
        self.hand_posit = 0                          # internal positive-match counter
        self.still_hold = False                      # flag to prevent double countdown
        self.current_pose = 1                        # index of current exercise pose
        self.key = ""
        self.is_pass = False
        self.round = 0                               # repetition counter (per-set)
        self.set = 0                                 # sets completed
        self.pose_name = [
            "placeholder",
            "เหยียดมือตรง",
            "ทำมือคล้ายตะขอ",
            "กำมือ",
            "กำมือแบบเหยียดปลายนิ้ว",
            "งอโค้นนิ้วแต่เหยียดปลายนิ้วมือ"
        ]
        self.extent = 0
        self.progress = 0

        # --------------------
        # Camera setup
        # --------------------
        # OpenCV VideoCapture is used by the background MediaPipe thread.
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            # Fail gracefully: print message; UI will show placeholder until camera available.
            print("Error: Cannot open webcam")
        else:
            print("✓ Camera opened successfully")
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            print(f"✓ Camera set to: {self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")

        # --------------------
        # UI theming constants
        # --------------------
        # Centralized colors and fonts allow consistent styling.
        self.purple_bg = "#6a0dad"
        self.light_gray_bg = "#d9d9d9"
        self.light_gray_bg_program = "white"
        self.red_btn = "#ff5656"
        self.hover_red_bt = "#cc4444"
        self.yellow_btn = "#fbbc05"
        self.hover_yellow_bt = "#e0a800"
        self.green_btn = "#34a853"
        self.hover_green_bt = "#247539"
        self.white_fg = "#ffffff"
        self.black_fg = "black"

        # Font definitions (Sarabun used in the original; fallback handled by system)
        self.font_large_title = ("Sarabun", 60, "bold")
        self.font_medium_text = ("Sarabun", 50, "bold")
        self.font_timer = ("Sarabun", 60, "bold")
        self.font_pose_text = ("Sarabun", 50, "bold")

        # --------------------------------------------------------------------
        # Top bar / header
        # --------------------------------------------------------------------
        # Contains logo and application title. Uses try/except to gracefully
        # fall back to text if the logo file is missing.
        self.top_bar_frame = ctk.CTkFrame(self, fg_color=self.purple_bg, height=150)
        self.top_bar_frame.pack(side="top", fill="x")
        self.top_bar_frame.pack_propagate(False)

        try:
            logo_image_pil = Image.open("pictures/logo.png")
            logo_image_pil = logo_image_pil.resize((140, 140))
            self.logo_photo = ImageTk.PhotoImage(logo_image_pil)
            self.logo_label = ctk.CTkLabel(
                self.top_bar_frame, image=self.logo_photo, fg_color=self.purple_bg, text=""
            )
            self.logo_label.pack(side="left", padx=20, pady=10)
        except FileNotFoundError:
            # Keep a clean textual placeholder instead of crashing.
            self.logo_label = ctk.CTkLabel(
                self.top_bar_frame, text="LOGO", font=("Sarabun", 20), text_color=self.white_fg, fg_color=self.purple_bg
            )
            self.logo_label.pack(side="left", padx=20, pady=10)
            print("Warning: logo.png not found. Using text placeholder.")

        # Title label (large, left side)
        self.app_title_label = ctk.CTkLabel(
            self.top_bar_frame,
            text="AI-Powered Anti-trigger Fingers",
            font=self.font_large_title,
            text_color=self.white_fg,
            fg_color=self.purple_bg,
        )
        self.app_title_label.pack(side="left", padx=20, pady=10)

        # --------------------------------------------------------------------
        # Main content layout (grid)
        # --------------------------------------------------------------------
        # The main_content_frame uses a 3-column grid:
        #   column 0 = camera preview (left)
        #   column 1 = pose/sets info (center)
        #   column 2 = timer + example pose (right)
        self.main_content_frame = ctk.CTkFrame(self, fg_color=self.light_gray_bg_program)
        self.main_content_frame.pack(side="top", fill="both", expand=True, pady=20)
        self.main_content_frame.grid_columnconfigure(0, weight=1, minsize=600)
        self.main_content_frame.grid_columnconfigure(1, weight=1, minsize=600)
        self.main_content_frame.grid_columnconfigure(2, weight=1, minsize=600)
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(1, weight=1)
        self.main_content_frame.grid_rowconfigure(2, weight=1)

        # --------------------------------------------------------------------
        # Left column: live camera preview
        # --------------------------------------------------------------------
        # We prepare a placeholder image so that the UI label always has an image
        # object (avoids Tkinter 'image garbage collected' problems).
        self.camera_width = 400
        self.camera_height = 570
        placeholder = Image.new("RGB", (self.camera_width, self.camera_height), (200, 200, 200))
        self.camera_photo = ImageTk.PhotoImage(placeholder)
        self.camera_label = ctk.CTkLabel(self.main_content_frame, image=self.camera_photo, text="")
        self.camera_label.grid(row=0, column=0, rowspan=3, padx=40, pady=20, sticky="nsew")

        # --------------------------------------------------------------------
        # Middle column: sets & rounds + pose textual description
        # --------------------------------------------------------------------
        # This area shows current repetition count and the name of the pose.
        self.set_times_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg, border_width=1)
        self.set_times_frame.grid(row=0, column=1, padx=20, pady=10, sticky="ew")
        self.times_line_frame = ctk.CTkFrame(self.set_times_frame, fg_color=self.light_gray_bg)
        self.times_line_frame.pack(side="top", pady=(10, 0))
        self.Label_times_text = ctk.CTkLabel(
            self.times_line_frame,
            text="ครั้งที่ : ",
            font=self.font_medium_text,
            text_color=self.black_fg,
            fg_color=self.light_gray_bg,
        )
        self.Label_times_text.pack(side="left", padx=(10, 0))
        self.Label_set_times_number = ctk.CTkLabel(
            self.times_line_frame, text=f"{self.round}", font=self.font_medium_text, text_color=self.black_fg, fg_color=self.light_gray_bg
        )
        self.Label_set_times_number.pack(side="left", padx=(0, 10))
        self.sets_line_frame = ctk.CTkFrame(self.set_times_frame, fg_color=self.light_gray_bg)
        self.sets_line_frame.pack(side="top", pady=(0, 10))
        self.Label_set_text = ctk.CTkLabel(
            self.sets_line_frame, text="เซ็ตที่ : ", font=self.font_medium_text, text_color=self.black_fg, fg_color=self.light_gray_bg
        )
        self.Label_set_text.pack(side="left", padx=(10, 0))
        self.Label_set_number = ctk.CTkLabel(
            self.sets_line_frame, text=f"{self.set}", font=self.font_medium_text, text_color=self.black_fg, fg_color=self.light_gray_bg
        )
        self.Label_set_number.pack(side="left", padx=(0, 10))

        # Pose description block
        self.pose_text_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg, border_width=1)
        self.pose_text_frame.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        self.Label_pose_thai_text = ctk.CTkLabel(
            self.pose_text_frame, text=f"ท่าที่ {self.current_pose}", font=self.font_pose_text, text_color=self.black_fg, fg_color=self.light_gray_bg
        )
        self.Label_pose_thai_text.pack(side="top", pady=(10, 0))
        self.Label_pose_action_text = ctk.CTkLabel(
            self.pose_text_frame, text=f"{self.pose_name[self.current_pose]}", font=self.font_pose_text, text_color=self.black_fg, fg_color=self.light_gray_bg
        )
        self.Label_pose_action_text.pack(side="top", pady=(0, 10))

        # --------------------------------------------------------------------
        # Bottom controls: Start / Reset
        # --------------------------------------------------------------------
        # Big buttons for touch-friendly interaction in kiosk mode.
        self.controls_center_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg_program)
        self.controls_center_frame.grid(row=2, column=0, columnspan=3, pady=(10, 20), sticky="ew")
        self.buttons_inner = ctk.CTkFrame(self.controls_center_frame, fg_color=self.light_gray_bg_program)
        self.buttons_inner.pack(expand=True)
        self.start_stop_button = ctk.CTkButton(
            self.buttons_inner,
            text="เริ่มต้น",
            font=("Sarabun", 50, "bold"),
            fg_color=self.green_btn,
            text_color=self.white_fg,
            command=lambda: self.toggle_start_pause(),
            height=80,
            width=260,
            hover_color=self.hover_green_bt,
        )
        self.start_stop_button.grid(row=0, column=0, padx=50, pady=5)
        self.reset_button = ctk.CTkButton(
            self.buttons_inner,
            text="รีเซ็ต",
            font=("Sarabun", 50, "bold"),
            fg_color=self.red_btn,
            text_color=self.white_fg,
            command=lambda: self.reset_action(),
            height=80,
            width=260,
            hover_color=self.hover_red_bt,
        )
        self.reset_button.grid(row=0, column=1, padx=30, pady=5)

        # --------------------------------------------------------------------
        # Right column top: Timer circle + animated progress arc
        # --------------------------------------------------------------------
        self.timer_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.white_fg)
        self.timer_frame.grid(row=0, column=2, padx=20, pady=20, sticky="n")
        self.timer_canvas_size = 260
        self.timer_pad = 10
        self.timer_canvas = ctk.CTkCanvas(
            self.timer_frame, width=self.timer_canvas_size, height=self.timer_canvas_size, bg=self.white_fg, highlightthickness=0
        )
        self.timer_canvas.pack()
        left = self.timer_pad
        top = self.timer_pad
        right = self.timer_canvas_size - self.timer_pad
        bottom = self.timer_canvas_size - self.timer_pad
        # draw initial neutral circle
        self.timer_canvas.create_oval(left, top, right, bottom, outline="#3CB371", width=10, tags="progress")
        center = self.timer_canvas_size // 2
        self.timer_text = self.timer_canvas.create_text(center, center, text=f"{self.time_current}", font=self.font_timer, fill=self.black_fg)

        # Timer animation bookkeeping variables (used by _animate_timer)
        self.timer_anim_job = None
        self._timer_anim_from = 0.0
        self._timer_anim_to = 0.0
        self._timer_anim_start = 0.0
        self._timer_anim_duration = 0.0

        # --------------------------------------------------------------------
        # Right column bottom: example pose (small image) + history button
        # --------------------------------------------------------------------
        # Load example pose image if it exists; otherwise show placeholder text.
        try:
            small_hand_image_pil = Image.open("pictures/EX_POSE/pose1.png")
            small_hand_image_pil = small_hand_image_pil.resize((300, 300), Image.LANCZOS)
            self.small_hand_photo = ImageTk.PhotoImage(small_hand_image_pil)
            self.small_hand_label = ctk.CTkLabel(self.main_content_frame, image=self.small_hand_photo, text="")
            self.small_hand_label.grid(row=1, column=2, padx=20, pady=(0, 20), sticky="n")
        except FileNotFoundError:
            # Keep a clear textual placeholder instead of failing.
            self.small_hand_label = ctk.CTkLabel(
                self.main_content_frame, text="Small Hand\nImage\n(Placeholder)", font=("Sarabun", 16), bg="lightgray", width=15, height=10
            )
            self.small_hand_label.grid(row=1, column=2, padx=20, pady=(0, 20), sticky="n")
            print("Warning: small_hand.png not found. Using text placeholder.")

        # History / report button
        self.small_hand_bottom_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg_program)
        self.small_hand_bottom_frame.grid(row=2, column=2, pady=(0, 20))
        self.log_button = ctk.CTkButton(
            self.small_hand_bottom_frame,
            text="รายงาน",
            font=("Sarabun", 50, "bold"),
            fg_color="#4285F4",
            text_color=self.white_fg,
            command=lambda: self.show_history_page(),
            height=80,
            width=240,
            hover_color="#3367D6",
        )
        self.log_button.pack(side="right", padx=140)

        # --------------------------------------------------------------------
        # History page: separate frame shown when user clicks "รายงาน"
        # --------------------------------------------------------------------
        self.history_page = ctk.CTkFrame(self, fg_color=self.light_gray_bg_program)
        self.history_title = ctk.CTkLabel(self.history_page, text="รายงานย้อนหลัง", font=("Sarabun", 55, "bold"), text_color=self.black_fg)
        self.history_title.pack(pady=5)
        
        # Chart container (กราฟอยู่บนสุด)
        self.chart_container = tk.Frame(
            self.history_page,
            bg="white"
        )
        self.chart_container.pack(fill="both", expand=True, padx=40, pady=(10, 5))
        self.history_content_frame = ctk.CTkFrame(self.history_page, fg_color=self.light_gray_bg_program)
        self.history_content_frame.pack(fill="x", padx=40, pady=(0, 0))

        # Text box (ซ้าย)
        self.history_textbox = ctk.CTkTextbox(
            self.history_content_frame,
            width=1000,
            height=250,
            font=("Sarabun", 20),
            text_color=self.black_fg,
            fg_color="#CCC9C9",
        )
        self.history_textbox.pack(side="left", padx=100, pady=(0, 0))

        # ปุ่มกลับ (ขวา บรรทัดเดียวกัน)
        self.back_button = ctk.CTkButton(
            self.history_content_frame,
            text="กลับ",
            font=("Sarabun", 40, "bold"),
            fg_color="#FF9800",
            text_color="white",
            hover_color="#E68900",
            command=self.show_main_page,
            height=80,
            width=260
        )
        self.back_button.pack(side="right", padx=(70, 100), pady=(100, 0))

        self.pose_sounds = {1: ["001.mp3"], 2: ["002.mp3"], 3: ["003.mp3"], 4: ["004.mp3"], 5: ["005.mp3"]}
        
        # ============ HELPER: GET HISTORY FROM FILE ============
        self.current_chart = None

        # ============ SOUND SETUP ============
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            # Non-fatal: continue without audio
            print(f"[Sound] Pygame mixer init error: {e}")

        # ============ RUNTIME STATE ============
        self.running = False
        self.countdown_active = False
        self.countdown_job = None
        self.countdown_total = 0
        self.countdown_end_time = 0

        # ============ START MEDIAPIPE THREAD ============
        self.mp_running = True
        self.mp_thread = threading.Thread(target=self._mediapipe_loop, daemon=True)
        self.mp_thread.start()

        self.check_sensor_loop()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def get_history_from_file(self):
        """Read history from file and return processed data"""
        FILE_PATH = "Anti-Finger.txt"
        daily_counts = defaultdict(int)
        if not os.path.exists(FILE_PATH):
            return []

        try:
            with open(FILE_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        date_str = line.split("]")[0][1:]
                        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        daily_counts[date.date()] += 1
                    except:
                        continue
        except Exception as e:
            print(f"Error reading file: {e}")
            return []

        history = []
        if not daily_counts:
            return history

        first_day = min(daily_counts.keys())
        last_day = max(daily_counts.keys())
        day = first_day
        
        while day <= last_day:
            count = daily_counts.get(day, 0)
            sets_done = count // 10
            progress = min((count / 30) * 100, 100) if count > 0 else 0
            history.append({
                'date': datetime.combine(day, datetime.min.time()),
                'progress': progress,
                'sets_done': sets_done,
                'count': count
            })
            day += timedelta(days=1)

        history.sort(key=lambda x: x['date'])
        return history

    def draw_progress_chart(self):
        """Draw the progress chart in history page"""
        history = self.get_history_from_file()
        
        # Clear previous chart
        for widget in self.chart_container.winfo_children():
            widget.destroy()

        if not history:
            label = tk.Label(self.chart_container, text="No data available", bg="white", font=("Sarabun", 14))
            label.pack(fill="both", expand=True)
            return

        try:
            # Main frame สำหรับ chart + control
            main_frame = tk.Frame(self.chart_container, bg="white")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Chart frame (ซ้าย)
            chart_frame = tk.Frame(main_frame, bg="white")
            chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Control frame (ขวา)
            control_frame = tk.Frame(main_frame, bg="white", width=200, height=400)
            control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)
            control_frame.pack_propagate(False)

            # Dropdown เลือกวัน
            tk.Label(control_frame, text="Select Date:", bg="white", font=("Sarabun", 14)).pack(anchor='w', pady=5)
            date_var = tk.StringVar()
            date_combo = ttk.Combobox(control_frame, textvariable=date_var, width=15, state='readonly')
            date_combo.pack(anchor='w', padx=5)

            # Legend
            tk.Label(control_frame, text="\nLegend", bg="white", font=("Sarabun", 12, "bold")).pack(anchor='w', pady=(10, 5))
            tk.Label(control_frame, text="🔴 Red: <50%", bg="white", fg="red", font=("Sarabun", 12)).pack(anchor='w')
            tk.Label(control_frame, text="🟢 Green: ≥50%", bg="white", fg="green", font=("Sarabun", 12)).pack(anchor='w')
            tk.Label(control_frame, text="↑ ดีขึ้น", bg="white", fg="green", font=("Sarabun", 12)).pack(anchor='w')
            tk.Label(control_frame, text="↓ แย่ลง", bg="white", fg="orange", font=("Sarabun", 12)).pack(anchor='w')

            # Feedback label
            feedback_label = tk.Label(control_frame, text="", bg="lightyellow", justify='left', wraplength=400, 
                                     font=("Sarabun", 12), relief=tk.SUNKEN, padx=5, pady=5)
            feedback_label.pack(fill='x', pady=10, padx=5)

            # Create chart
            fig, ax = plt.subplots(figsize=(12, 5), dpi=80)
            fig.patch.set_facecolor('white')

            dates = [h['date'] for h in history]
            progresses = [h['progress'] for h in history]

            # Prepare OHLC data
            o, h_, l, c = [], [], [], []
            prev = progresses[0] if progresses else 0
            
            for p in progresses:
                o.append(prev)
                c.append(p)
                high = max(prev, p)
                low = min(prev, p)
                h_.append(high)
                l.append(low)
                prev = p

            # Draw bars and lines
            points = []
            for i, p in enumerate(progresses):
                prev_prog = progresses[i-1] if i > 0 else None
                
                if prev_prog is None:
                    color = (1, 0, 0) if p < 50 else (0, 1, 0)
                elif p > prev_prog:
                    color = (0, 1, 0)
                elif p < prev_prog:
                    color = (1, 0.65, 0)
                else:
                    color = (1, 0, 0) if p < 50 else (0, 1, 0)

                ax.vlines(dates[i], l[i], h_[i], color=color, linewidth=2)
                ax.vlines(dates[i], o[i], c[i], color=color, linewidth=8)
                
                if prev_prog is not None:
                    if p > prev_prog:
                        ax.annotate('↑', xy=(dates[i], c[i]+3), ha='center', color='green', fontsize=12)
                    elif p < prev_prog:
                        ax.annotate('↓', xy=(dates[i], c[i]+3), ha='center', color='black', fontsize=12)
                
                point, = ax.plot(dates[i], c[i], 'o', color='black', markersize=8)
                points.append((point, dates[i], p, history[i]['sets_done'], i))

            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
            ax.set_ylabel("ความสำเร็จ (%)", font={'family': 'Sarabun', 'size': 18, 'weight': 'bold'})
            ax.set_ylim(0, 110)
            ax.set_title("สถิติของคุณ", font={'family': 'Sarabun', 'size': 18, 'weight': 'bold'})
            ax.grid(True, linestyle='--', alpha=0.5)
            fig.autofmt_xdate()
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

            # Populate date combo
            date_list = [h['date'].strftime('%d-%b-%Y') for h in history]
            date_combo['values'] = date_list
            if date_list:
                date_combo.set(date_list[-1])

            def feedback_text(prog, prev_prog):
                if prog == 0:
                    return "วันนี้คุณยังไม่ได้ทำ 🔴"
                elif prev_prog is not None and prog < prev_prog:
                    return "วันนี้คุณทำได้น้อยลง ↓"
                elif prev_prog is not None and prog > prev_prog:
                    return "วันนี้คุณทำได้ดีขึ้น ↑"
                elif prog < 50:
                    return "วันนี้คุณทำได้น้อยลง ↓"
                else:
                    return "วันนี้คุณทำได้ตามปกติ ✓"

            def update_feedback(event=None):
                selected_date_str = date_var.get()
                if not selected_date_str:
                    return
                try:
                    selected_date = datetime.strptime(selected_date_str, '%d-%b-%Y').date()
                    idx = next((i for i, h in enumerate(history) if h['date'].date() == selected_date), None)
                    if idx is not None:
                        prog = history[idx]['progress']
                        sets = history[idx]['sets_done']
                        prev_prog = history[idx-1]['progress'] if idx > 0 else None
                        fb = feedback_text(prog, prev_prog)
                        feedback_label.config(text=f"{selected_date_str}\nProgress: {prog:.0f}%\nSets: {sets}\n{fb}")
                except Exception as e:
                    print(f"Error: {e}")

            def on_click(event):
                if event.inaxes != ax:
                    return
                for point, date, prog, sets, idx in points:
                    xdata = mdates.date2num(date)
                    ydata = prog
                    if abs(event.xdata - xdata) < 0.3 and abs(event.ydata - ydata) < 5:
                        prev_prog = progresses[idx-1] if idx > 0 else None
                        fb = feedback_text(prog, prev_prog)
                        feedback_label.config(text=f"{date.strftime('%d-%b-%Y')}\nProgress: {prog:.0f}%\nSets: {sets}\n{fb}")
                        date_var.set(date.strftime('%d-%b-%Y'))
                        return

            date_combo.bind("<<ComboboxSelected>>", update_feedback)
            canvas.mpl_connect("button_press_event", on_click)

            # Show initial feedback
            update_feedback()

            self.current_chart = (fig, canvas)

        except Exception as e:
            print(f"Error drawing chart: {e}")
            label = tk.Label(self.chart_container, text=f"Error: {e}", bg="white", font=("Sarabun", 12), fg="red")
            label.pack(fill="both", expand=True)

    # ============ PLAY SOUND ============
    def play_sounds_sequential(self, filename):
        """Play a short sound file from Voices/ on a daemon thread."""
        def _play(f=filename):
            try:
                if not f.endswith(".mp3"):
                    f += ".mp3"
                sound_path = f"Voices/{f}"
                if os.path.exists(sound_path):
                    sound = pygame.mixer.Sound(sound_path)
                    sound.play()
            except Exception as e:
                print(f"Sound error: {e}")

        threading.Thread(target=_play, daemon=True).start()

    # ============ HISTORY UI ============
    def load_history(self):
        """Load history text from file"""
        try:
            with open("Anti-Finger.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = ["No history found.\n"]

        max_lines = 1000000000000
        if len(lines) > max_lines:
            lines = lines[-max_lines:]

        self.history_textbox.configure(state="normal")
        self.history_textbox.delete("1.0", "end")
        self.history_textbox.insert("end", "".join(lines))
        self.history_textbox.see("end")
        self.history_textbox.configure(state="disabled")

    def show_main_page(self):
        self.history_page.pack_forget()
        self.main_content_frame.pack(side="top", fill="both", expand=True, pady=20)
        self.play_sounds_sequential("010.mp3")

    def show_history_page(self):
        self.main_content_frame.pack_forget()
        self.play_sounds_sequential("009.mp3")
        self.history_page.pack(side="top", fill="both", expand=True, pady=20)
        self.draw_progress_chart()
        self.load_history()

    def write_log(self, message):
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{now} เซ็ตที่ {self.set} ครั้งที่ {self.round} : {message}"
        try:
            with open("Anti-Finger.txt", "a", encoding="utf-8") as f:
                f.write(log_message + "\n")
            print(log_message)
        except Exception as e:
            print(f"Error writing log: {e}")

    # ============ CAMERA CHECK (FALLBACK) ============
    def check_fingers(self):
        try:
            ret, frame = self.cap.read()
            if not ret:
                return
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
            white_pixels = cv2.countNonZero(thresh)
            if white_pixels > 50000:
                if self.hand_posit < 5:
                    self.hand_posit += 1
        except Exception as e:
            print(f"[check_fingers] Error: {e}")

    # ============ MEDIAPIPE BACKGROUND LOOP ============
    def _mediapipe_loop(self):
        """Background MediaPipe detection thread"""
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        drawing_spec_landmark = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4)
        drawing_spec_connection = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)

        hands = mp_hands.Hands(
            static_image_mode=False, max_num_hands=1,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        )

        pose_ranges = {
            1: [(0, 200), (150, 185), (150, 185), (150, 185), (150, 185)],
            2: [(0, 200), (40, 170), (40, 170), (40, 170), (40, 170)],
            3: [(0, 200), (0, 60), (0, 60), (0, 60), (0, 60)],
            4: [(0, 200), (0, 50), (0, 50), (0, 50), (0, 50)],
            5: [(0, 200), (50, 185), (50, 185), (50, 160), (50, 160)],
        }

        def _angle_between(a, b):
            import math
            ax, ay = a
            bx, by = b
            dot = ax * bx + ay * by
            na = (ax * ax + ay * ay) ** 0.5
            nb = (bx * bx + by * by) ** 0.5
            if na == 0 or nb == 0:
                return 0.0
            cosv = max(-1.0, min(1.0, dot / (na * nb)))
            return math.degrees(math.acos(cosv))

        try:
            while self.mp_running:
                ret, frame = self.cap.read()
                if not ret:
                    print("[MediaPipe] Frame capture failed, retrying...")
                    time.sleep(0.01)
                    continue

                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                # Initialize angles with default values
                thumb_a = index_a = middle_a = ring_a = pinky_a = 0
                pose_match = False

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(
                            frame, hand_landmarks, mp_hands.HAND_CONNECTIONS,
                            drawing_spec_landmark, drawing_spec_connection
                        )

                        lm = hand_landmarks.landmark

                        def to_pt(idx):
                            return (lm[idx].x * w, lm[idx].y * h)

                        wrist = to_pt(0)

                        # Thumb
                        v1 = (to_pt(4)[0] - to_pt(2)[0], to_pt(4)[1] - to_pt(2)[1])
                        v2 = (wrist[0] - to_pt(2)[0], wrist[1] - to_pt(2)[1])
                        thumb_a = _angle_between(v1, v2)

                        # Index
                        v1 = (to_pt(8)[0] - to_pt(5)[0], to_pt(8)[1] - to_pt(5)[1])
                        v2 = (wrist[0] - to_pt(5)[0], wrist[1] - to_pt(5)[1])
                        index_a = _angle_between(v1, v2)

                        # Middle
                        v1 = (to_pt(12)[0] - to_pt(9)[0], to_pt(12)[1] - to_pt(9)[1])
                        v2 = (wrist[0] - to_pt(9)[0], wrist[1] - to_pt(9)[1])
                        middle_a = _angle_between(v1, v2)

                        # Ring
                        v1 = (to_pt(16)[0] - to_pt(13)[0], to_pt(16)[1] - to_pt(13)[1])
                        v2 = (wrist[0] - to_pt(13)[0], wrist[1] - to_pt(13)[1])
                        ring_a = _angle_between(v1, v2)

                        # Pinky
                        v1 = (to_pt(20)[0] - to_pt(17)[0], to_pt(20)[1] - to_pt(17)[1])
                        v2 = (wrist[0] - to_pt(17)[0], wrist[1] - to_pt(17)[1])
                        pinky_a = _angle_between(v1, v2)

                        reqs = pose_ranges.get(self.current_pose, pose_ranges[1])
                        angles = [thumb_a, index_a, middle_a, ring_a, pinky_a]
                        
                        ok = True
                        for ang, (mn, mx) in zip(angles, reqs):
                            if ang is None or not (mn <= ang <= mx):
                                ok = False
                                break
                        pose_match = ok

                        try:
                            cv2.putText(frame, f"Match:{'YES' if pose_match else 'NO'}", (10, 180),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0) if pose_match else (0, 0, 200), 2)
                        except Exception:
                            pass

                display_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(display_rgb)

                def _crop_and_resize(img, target_w, target_h):
                    src_w, src_h = img.size
                    target_ratio = target_w / target_h
                    src_ratio = src_w / src_h
                    if src_ratio > target_ratio:
                        new_w = int(src_h * target_ratio)
                        left = (src_w - new_w) // 2
                        img = img.crop((left, 0, left + new_w, src_h))
                    else:
                        new_h = int(src_w / target_ratio)
                        top = (src_h - new_h) // 2
                        img = img.crop((0, top, src_w, top + new_h))
                    return img.resize((target_w, target_h), Image.LANCZOS)

                pil_img = _crop_and_resize(pil_img, self.camera_width, self.camera_height)

                try:
                    self.after(0, lambda im=pil_img, a=(thumb_a, index_a, middle_a, ring_a, pinky_a), m=pose_match: (
                        self._update_camera_label(im),
                        self._apply_pose_detection(a, m)
                    ))
                except RuntimeError:
                    break

                time.sleep(0.02)
        finally:
            hands.close()

    def _apply_pose_detection(self, angles, match):
        try:
            if match:
                if self.hand_posit < 5:
                    self.hand_posit += 1
            else:
                self.hand_posit = 0
        except Exception as e:
            print(f"[Pose Apply] {e}")

    def _update_camera_label(self, pil_image):
        try:
            self.camera_photo = ImageTk.PhotoImage(pil_image)
            self.camera_label.configure(image=self.camera_photo)
        except Exception as e:
            print(f"[Camera Update] {e}")

    def timer_reset(self):
        self.time_current = self.time_max
        self.hand_posit = 0
        self.update_timer()
        self.reset_pic()
        try:
            self.update_EX_pose()
        except Exception:
            pass

    def update_pic(self):
        return

    def reset_pic(self):
        self.timer_canvas.delete("progress")
        l = self.timer_pad
        r = self.timer_canvas_size - self.timer_pad
        self.timer_canvas.create_oval(l, l, r, r, outline="#3CB371", width=10, tags="progress")

    def update_timer(self):
        try:
            prev_time = self.time_current + 1
            from_prog = max(0.0, min(1.0, (self.time_max - prev_time) / float(self.time_max)))
            to_prog = max(0.0, min(1.0, (self.time_max - self.time_current) / float(self.time_max)))

            self._stop_timer_animation()

            self._timer_prev_sec = prev_time
            self._timer_anim_from = from_prog
            self._timer_anim_to = to_prog
            self._timer_anim_start = time.time()
            self._timer_anim_duration = 1.0
            self.timer_anim_job = self.after(0, self._animate_timer)
        except Exception as e:
            print(f"[update_timer] {e}")

    def _animate_timer(self):
        try:
            now = time.time()
            elapsed = now - self._timer_anim_start
            t = min(1.0, max(0.0, elapsed / float(self._timer_anim_duration)))
            progress = self._timer_anim_from + (self._timer_anim_to - self._timer_anim_from) * t
            extent = 360 * progress

            self.timer_canvas.delete("progress")
            l = self.timer_pad
            r = self.timer_canvas_size - self.timer_pad
            self.timer_canvas.create_arc(l, l, r, r, start=-90, extent=-extent, style="arc", width=10, outline="#3CB371", tags="progress")

            try:
                prev = getattr(self, "_timer_prev_sec", self.time_current + 1)
                interp = prev + (self.time_current - prev) * t
                interp = max(float(self.time_current), min(float(prev), interp))
                secs = int(__import__("math").ceil(interp))
            except Exception:
                secs = int(max(0, self.time_current))
            self.timer_canvas.itemconfig(self.timer_text, text=str(secs))

            if t < 1.0:
                self.timer_anim_job = self.after(50, self._animate_timer)
            else:
                self.timer_anim_job = None
                self.timer_canvas.delete("progress")
                l = self.timer_pad
                r = self.timer_canvas_size - self.timer_pad
                self.timer_canvas.create_arc(l, l, r, r, start=-90, extent=-360 * self._timer_anim_to, style="arc", width=10, outline="#3CB371", tags="progress")
                self.timer_canvas.itemconfig(self.timer_text, text=str(self.time_current))
        except Exception as e:
            print(f"[_animate_timer] {e}")
            self.timer_anim_job = None

    def _stop_timer_animation(self):
        try:
            if self.timer_anim_job:
                try:
                    self.after_cancel(self.timer_anim_job)
                except Exception:
                    pass
                self.timer_anim_job = None
            progress = (self.time_max - self.time_current) / float(self.time_max) if self.time_max else 0.0
            extent = 360 * progress
            self.timer_canvas.delete("progress")
            l = self.timer_pad
            r = self.timer_canvas_size - self.timer_pad
            self.timer_canvas.create_arc(l, l, r, r, start=-90, extent=-extent, style="arc", width=10, outline="#3CB371", tags="progress")
            self.timer_canvas.itemconfig(self.timer_text, text=str(self.time_current))
        except Exception as e:
            print(f"[_stop_timer_animation] {e}")

    def update_text(self):
        self.Label_pose_action_text.configure(text=f"{self.pose_name[self.current_pose]}")
        self.Label_pose_thai_text.configure(text=f"ท่าที่ {self.current_pose}")

    def update_round(self):
        self.Label_set_times_number.configure(text=f"{self.round}")
        self.Label_set_number.configure(text=f"{self.set}")

    def update_EX_pose(self):
        try:
            small_hand_image_pil = Image.open(f"pictures/EX_POSE/pose{self.current_pose}.png")
            small_hand_image_pil = small_hand_image_pil.resize((300, 300))
            self.small_hand_photo = ImageTk.PhotoImage(small_hand_image_pil)
            self.small_hand_label.configure(image=self.small_hand_photo)
        except:
            pass

    def toggle_start_pause(self):
        if self.start_stop_button.cget("text") == "เริ่มต้น":
            self.start_stop_button.configure(text="หยุด", fg_color=self.yellow_btn, hover_color=self.hover_yellow_bt)
            self.start_pose_countdown(2)
            self.play_sounds_sequential("006.mp3")
            if self.current_pose == 1:
                try:
                    self.after(1500, lambda: self.play_sounds_sequential(self.pose_sounds[self.current_pose][0]))
                except Exception:
                    pass
        else:
            self.start_stop_button.configure(text="เริ่มต้น", fg_color=self.green_btn, hover_color=self.hover_green_bt)
            self.running = False
            self._cancel_countdown()
            self.play_sounds_sequential("007.mp3")

    def start_pose_countdown(self, seconds: int):
        self._cancel_countdown()
        self.countdown_active = True
        self.countdown_total = max(1, seconds)
        self.countdown_end_time = time.time() + self.countdown_total
        self.countdown_job = self.after(0, self._animate_countdown)

    def _animate_countdown(self):
        if not self.countdown_active:
            return
        import math, time as _time
        now = _time.time()
        remaining = self.countdown_end_time - now
        if remaining <= 0:
            self.countdown_active = False
            self.countdown_job = None
            self.running = True
            try:
                self.timer_canvas.itemconfig(self.timer_text, text=str(self.time_current))
                self.timer_canvas.delete("progress")
                l = self.timer_pad
                r = self.timer_canvas_size - self.timer_pad
                self.timer_canvas.create_oval(l, l, r, r, outline="#3CB371", width=10, tags="progress")
            except Exception:
                pass

        frac = max(0.0, min(1.0, remaining / float(self.countdown_total)))
        extent = 360 * frac

        try:
            self.timer_canvas.delete("progress")
            l = self.timer_pad
            r = self.timer_canvas_size - self.timer_pad
            self.timer_canvas.create_arc(l, l, r, r, start=-90, extent=-extent, style="arc", width=10, outline="#FFA500", tags="progress")
            secs = int(math.ceil(remaining))
            self.timer_canvas.itemconfig(self.timer_text, text=str(secs))
        except Exception:
            pass

        try:
            self.countdown_job = self.after(50, self._animate_countdown)
        except Exception:
            self.countdown_active = False
            self.countdown_job = None

    def _cancel_countdown(self):
        if self.countdown_active:
            self.countdown_active = False
            if self.countdown_job:
                try:
                    self.after_cancel(self.countdown_job)
                except Exception:
                    pass
                self.countdown_job = None
            try:
                self.timer_canvas.itemconfig(self.timer_text, text=str(self.time_current))
                self.timer_canvas.delete("progress")
                l = self.timer_pad
                r = self.timer_canvas_size - self.timer_pad
                self.timer_canvas.create_oval(l, l, r, r, outline="#3CB371", width=10, tags="progress")
            except Exception:
                pass

    def reset_action(self):
        self.running = False
        try:
            self._cancel_countdown()
        except Exception:
            pass

        self.start_stop_button.configure(text="เริ่มต้น", fg_color=self.green_btn, hover_color=self.hover_green_bt)
        self.round = 0
        self.set = 0
        self.current_pose = 1
        self.timer_reset()
        self.update_text()
        self.update_round()

        try:
            self.play_sounds_sequential("008.mp3")
        except Exception as e:
            print(f"[reset_action] play sound error: {e}")

    def on_close(self):
        self.mp_running = False
        self.running = False
        try:
            if hasattr(self, "mp_thread") and self.mp_thread.is_alive():
                self.mp_thread.join(timeout=1.0)
        except Exception:
            pass
        try:
            if self.cap is not None and self.cap.isOpened():
                self.cap.release()
        except Exception:
            pass
        self.destroy()
        os._exit(0)
        
    def check_sensor_loop(self):
        if self.running:
            try:
                self.check_fingers()
            except Exception as e:
                print(f"[check_sensor_loop] check_fingers error: {e}")

            if self.hand_posit == 5 and self.time_current > 0 and not self.still_hold:
                try:
                    self.time_current -= 1
                    self.update_timer()
                except Exception as e:
                    print(f"[check_sensor_loop] timer update error: {e}")

                if self.time_current <= 0:
                    try:
                        delay_ms = int(getattr(self, "_timer_anim_duration", 1.0) * 1000) + 50
                        self.after(delay_ms, self._on_pose_success)
                    except Exception as e:
                        print(f"[check_sensor_loop] scheduling _on_pose_success error: {e}")

        try:
            self.after(1000, self.check_sensor_loop)
        except Exception as e:
            print(f"[check_sensor_loop] scheduling error: {e}")

    def _on_pose_success(self):
        try:
            if self.time_current > 0:
                return
            self.write_log(f"ท่า{self.pose_name[self.current_pose]}สำเร็จ!")
        except Exception as e:
            print(f"[_on_pose_success] write_log error: {e}")

        self.current_pose += 1
        if self.current_pose > 5:
            self.current_pose = 1
            self.round += 1
            if self.round >= 10:
                self.round = 0
                self.set += 1

        try:
            self.update_round()
            self.timer_reset()
            self.update_EX_pose()
            self.update_text()
            sound_file = self.pose_sounds.get(self.current_pose, [None])[0]
            if sound_file:
                try:
                    self.play_sounds_sequential(sound_file)
                except Exception as e:
                    print(f"[_on_pose_success] play sound error: {e}")
        except Exception as e:
            print(f"[_on_pose_success] error: {e}")


# --- Run App ---
if __name__ == "__main__":
    app = AntiTriggerFingersApp()
    app.mainloop()