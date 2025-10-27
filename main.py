from PIL import Image, ImageTk
import customtkinter as ctk
import threading
import time
from datetime import datetime
import pygame
import cv2  # สำหรับกล้อง
import mediapipe as mp  # added MediaPipe

# Brief module description: main GUI app that uses MediaPipe + OpenCV to detect hand poses,
# manage a smooth countdown/timer UI, play voice cues, and record simple history logs.

# --- Main Application Class: main window and controller for camera, MediaPipe processing, UI and training logic ---
class AntiTriggerFingersApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AI-Powered Anti-trigger Fingers")
        self.attributes("-fullscreen", True)
        self.geometry("1280x800+0+0")
        self.overrideredirect(True)
        self.bind("<Escape>", lambda e: self.on_close())
        self.resizable(False, False)
        self.configure(fg_color="#FFFFFF")

        # --- State Variables ---
        self.key_held = False
        self.time_max = 5
        self.time_current = self.time_max
        self.hand_posit = 0
        self.still_hold = False
        self.current_pose = 1
        self.key = ""
        self.is_pass = False
        self.round = 0
        self.set = 0
        self.pose_name = ["placeholder", "เหยียดมือตรง", "ทำมือคล้ายตะขอ", "กำมือ", "กำมือแบบเหยียดปลายนิ้ว", "งอโคนนิ้วแต่เหยียดปลายนิ้วมือ"]
        self.extent = 0
        self.progress = 0

        # --- Camera setup ---
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Error: Cannot open webcam")

        # --- UI Colors ---
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

        # --- Fonts ---
        self.font_large_title = ("Sarabun", 60, "bold")
        self.font_medium_text = ("Sarabun", 50 ,"bold")
        self.font_timer = ("Sarabun", 60, "bold")
        self.font_pose_text = ("Sarabun", 50, "bold")

        # --- Top Bar (Header) ---
        self.top_bar_frame = ctk.CTkFrame(self, fg_color=self.purple_bg, height=150)
        self.top_bar_frame.pack(side="top", fill="x")
        self.top_bar_frame.pack_propagate(False)

        try:
            logo_image_pil = Image.open("pictures/logo.png")
            logo_image_pil = logo_image_pil.resize((140, 140))
            self.logo_photo = ImageTk.PhotoImage(logo_image_pil)
            self.logo_label = ctk.CTkLabel(self.top_bar_frame, image=self.logo_photo, fg_color=self.purple_bg, text="")
            self.logo_label.pack(side="left", padx=20, pady=10)
        except FileNotFoundError:
            self.logo_label = ctk.CTkLabel(self.top_bar_frame, text="LOGO", font=("Sarabun", 20), fg=self.white_fg, bg=self.purple_bg)
            self.logo_label.pack(side="left", padx=20, pady=10)
            print("Warning: logo.png not found. Using text placeholder.")

        self.app_title_label = ctk.CTkLabel(self.top_bar_frame, text="AI-Powered Anti-trigger Fingers",
                                            font=self.font_large_title, text_color=self.white_fg, fg_color=self.purple_bg)
        self.app_title_label.pack(side="left", padx=20, pady=10)

        # --- Main Content Area ---
        self.main_content_frame = ctk.CTkFrame(self, fg_color=self.light_gray_bg_program)
        self.main_content_frame.pack(side="top", fill="both", expand=True, pady=20)
        self.main_content_frame.grid_columnconfigure(0, weight=1, minsize=600)
        self.main_content_frame.grid_columnconfigure(1, weight=1, minsize=600)
        self.main_content_frame.grid_columnconfigure(2, weight=1, minsize=600)
        self.main_content_frame.grid_rowconfigure(0, weight=1)
        self.main_content_frame.grid_rowconfigure(1, weight=1)
        self.main_content_frame.grid_rowconfigure(2, weight=1)

        # --- live camera (Left) --- 
        self.camera_width = 400
        self.camera_height = 450
        # placeholder image to avoid None
        placeholder = Image.new("RGB", (self.camera_width, self.camera_height), (200, 200, 200))
        self.camera_photo = ImageTk.PhotoImage(placeholder)
        self.camera_label = ctk.CTkLabel(self.main_content_frame, image=self.camera_photo, text="")
        self.camera_label.grid(row=0, column=0, rowspan=3, padx=40, pady=20, sticky="nsew")

        # --- Middle Column: Sets & Rounds info ---
        self.set_times_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg, border_width=1)
        self.set_times_frame.grid(row=0, column=1, padx=20, pady=10, sticky="ew")
        self.times_line_frame = ctk.CTkFrame(self.set_times_frame, fg_color=self.light_gray_bg)
        self.times_line_frame.pack(side="top", pady=(10,0))
        self.Label_times_text = ctk.CTkLabel(self.times_line_frame, text="ครั้งที่ : ", font=self.font_medium_text, text_color=self.black_fg, fg_color=self.light_gray_bg)
        self.Label_times_text.pack(side="left", padx=(10,0))
        self.Label_set_times_number = ctk.CTkLabel(self.times_line_frame, text=f"{self.round}", font=self.font_medium_text, text_color=self.black_fg, fg_color=self.light_gray_bg)
        self.Label_set_times_number.pack(side="left", padx=(0,10))
        self.sets_line_frame = ctk.CTkFrame(self.set_times_frame, fg_color=self.light_gray_bg)
        self.sets_line_frame.pack(side="top", pady=(0,10))
        self.Label_set_text = ctk.CTkLabel(self.sets_line_frame, text="เซ็ตที่ : ", font=self.font_medium_text, text_color=self.black_fg, fg_color=self.light_gray_bg)
        self.Label_set_text.pack(side="left", padx=(10,0))
        self.Label_set_number = ctk.CTkLabel(self.sets_line_frame, text=f"{self.set}", font=self.font_medium_text, text_color=self.black_fg, fg_color=self.light_gray_bg)
        self.Label_set_number.pack(side="left", padx=(0,10))

        # --- Pose Text ---
        self.pose_text_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg, border_width=1)
        self.pose_text_frame.grid(row=1, column=1, padx=20, pady=10, sticky="ew")
        self.Label_pose_thai_text = ctk.CTkLabel(self.pose_text_frame, text=f"ท่าที่ {self.current_pose}", font=self.font_pose_text, text_color=self.black_fg, fg_color=self.light_gray_bg)
        self.Label_pose_thai_text.pack(side="top", pady=(10,0))
        self.Label_pose_action_text = ctk.CTkLabel(self.pose_text_frame, text=f"{self.pose_name[self.current_pose]}", font=self.font_pose_text, text_color=self.black_fg, fg_color=self.light_gray_bg)
        self.Label_pose_action_text.pack(side="top", pady=(0,10))

        # --- Control Buttons (Start/Pause, Reset) ---
        self.controls_center_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg_program)
        self.controls_center_frame.grid(row=2, column=0, columnspan=3, pady=(10, 20), sticky="ew")
        self.buttons_inner = ctk.CTkFrame(self.controls_center_frame, fg_color=self.light_gray_bg_program)
        self.buttons_inner.pack(expand=True)
        self.start_stop_button = ctk.CTkButton(self.buttons_inner, text="เริ่มต้น", font=("Sarabun", 50, "bold"),
                                               fg_color=self.green_btn, text_color=self.white_fg,
                                               command=lambda: self.toggle_start_pause(), height=80, width=260, hover_color=self.hover_green_bt)
        self.start_stop_button.grid(row=0, column=0, padx=50, pady=5)
        self.reset_button = ctk.CTkButton(self.buttons_inner, text="รีเซ็ต", font=("Sarabun", 50, "bold"),
                                          fg_color=self.red_btn, text_color=self.white_fg,
                                          command=lambda: self.reset_action(), height=80, width=260, hover_color=self.hover_red_bt)
        self.reset_button.grid(row=0, column=1, padx=30, pady=5)

        # --- Timer Circle (Right Top) ---
        self.timer_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.white_fg)
        self.timer_frame.grid(row=0, column=2, padx=20, pady=20, sticky="n")
        self.timer_canvas_size = 260
        self.timer_pad = 10
        self.timer_canvas = ctk.CTkCanvas(self.timer_frame, width=self.timer_canvas_size, height=self.timer_canvas_size, bg=self.white_fg, highlightthickness=0)
        self.timer_canvas.pack()
        left = self.timer_pad
        top = self.timer_pad
        right = self.timer_canvas_size - self.timer_pad
        bottom = self.timer_canvas_size - self.timer_pad
        self.timer_canvas.create_oval(left, top, right, bottom, outline="#3CB371", width=10, tags="progress")
        center = self.timer_canvas_size // 2
        self.timer_text = self.timer_canvas.create_text(center, center, text=f"{self.time_current}", font=self.font_timer, fill=self.black_fg)

        # timer animation state
        self.timer_anim_job = None
        self._timer_anim_from = 0.0
        self._timer_anim_to = 0.0
        self._timer_anim_start = 0.0
        self._timer_anim_duration = 0.0

        # --- Small Pose Image (Right Bottom) ---
        try:
            small_hand_image_pil = Image.open("pictures/EX_POSE/pose1.png")
            small_hand_image_pil = small_hand_image_pil.resize((300, 300), Image.LANCZOS)
            self.small_hand_photo = ImageTk.PhotoImage(small_hand_image_pil)
            self.small_hand_label = ctk.CTkLabel(self.main_content_frame, image=self.small_hand_photo, text="")
            self.small_hand_label.grid(row=1, column=2, padx=20, pady=(0,20), sticky="n")
        except FileNotFoundError:
            self.small_hand_label = ctk.CTkLabel(self.main_content_frame, text="Small Hand\nImage\n(Placeholder)",
                                                 font=("Sarabun", 16), bg="lightgray", width=15, height=10)
            self.small_hand_label.grid(row=1, column=2, padx=20, pady=(0,20), sticky="n")
            print("Warning: small_hand.png not found. Using text placeholder.")
        self.small_hand_bottom_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.light_gray_bg_program)
        self.small_hand_bottom_frame.grid(row=2, column=2, pady=(0,20))
        self.log_button = ctk.CTkButton(self.small_hand_bottom_frame, text="รายงาน", font=("Sarabun", 50, "bold"),
                                        fg_color="#4285F4", text_color=self.white_fg,
                                        command=lambda: self.show_history_page(), height=80, width=240, hover_color="#3367D6")
        self.log_button.pack(side="right", padx=140)

        # --- Timer Circle (Right Top) ---
        self.timer_frame = ctk.CTkFrame(self.main_content_frame, fg_color=self.white_fg)
        self.timer_frame.grid(row=0, column=2, padx=20, pady=20, sticky="n")
        self.timer_canvas_size = 260
        self.timer_pad = 10
        self.timer_canvas = ctk.CTkCanvas(self.timer_frame, width=self.timer_canvas_size, height=self.timer_canvas_size, bg=self.white_fg, highlightthickness=0)
        self.timer_canvas.pack()
        left = self.timer_pad
        top = self.timer_pad
        right = self.timer_canvas_size - self.timer_pad
        bottom = self.timer_canvas_size - self.timer_pad
        self.timer_canvas.create_oval(left, top, right, bottom, outline="#3CB371", width=10, tags="progress")
        center = self.timer_canvas_size // 2
        self.timer_text = self.timer_canvas.create_text(center, center, text=f"{self.time_current}", font=self.font_timer, fill=self.black_fg)

        # timer animation state
        self.timer_anim_job = None
        self._timer_anim_from = 0.0
        self._timer_anim_to = 0.0
        self._timer_anim_start = 0.0
        self._timer_anim_duration = 0.0

        # --- Small Pose Image (Right Bottom) ---
        try:
            small_hand_image_pil = Image.open("pictures/EX_POSE/pose1.png")
            small_hand_image_pil = small_hand_image_pil.resize((300, 300), Image.LANCZOS)
            self.small_hand_photo = ImageTk.PhotoImage(small_hand_image_pil)
            self.small_hand_label = ctk.CTkLabel(self.main_content_frame, image=self.small_hand_photo, text="")
            self.small_hand_label.grid(row=1, column=2, padx=20, pady=(0,20), sticky="n")
        except FileNotFoundError:
            self.small_hand_label = ctk.CTkLabel(self.main_content_frame, text="Small Hand\nImage\n(Placeholder)",
                                                 font=("Sarabun", 16), bg="lightgray", width=15, height=10)
            self.small_hand_label.grid(row=1, column=2, padx=20, pady=(0,20), sticky="n")
            print("Warning: small_hand.png not found. Using text placeholder.")

        # --- History Page ---
        self.history_page = ctk.CTkFrame(self, fg_color=self.light_gray_bg_program)
        self.history_title = ctk.CTkLabel(self.history_page, text="รายงานย้อนหลัง",font=("Sarabun", 55 ,"bold"), text_color=self.black_fg)
        self.history_title.pack(pady=20)
        self.history_textbox = ctk.CTkTextbox(self.history_page, width=1000, height=500, font=("Sarabun", 20), text_color=self.black_fg, fg_color="#CCC9C9")
        self.history_textbox.pack(padx=40, pady=20)
        self.history_footer = ctk.CTkFrame(self.history_page, fg_color=self.light_gray_bg_program)
        self.history_footer.pack(fill="x", padx=40, pady=(0,20))
        self.back_button = ctk.CTkButton(self.history_footer, text="กลับ", font=("Sarabun", 40 ,"bold"), fg_color="#FF9800",
                                         text_color="white", hover_color="#E68900", command=lambda: self.show_main_page(), height=80, width=260)
        self.back_button.pack(side="right", padx=140, pady=10)

        # --- Sound setup ---
        self.pose_sounds = {1:["001.mp3"],2:["002.mp3"],3:["003.mp3"],4:["004.mp3"],5:["005.mp3"]}
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            print(f"[Sound] Pygame mixer init error: {e}")


        # --- Sensor loop replaced by camera ---
        self.running = False

        # countdown state for "start" (2s) before reading values
        self.countdown_active = False
        self.countdown_job = None
        self.countdown_remaining = 0

        # --- MediaPipe thread: runs always and updates camera preview + draws finger lines ---
        self.mp_running = True
        self.mp_thread = threading.Thread(target=self._mediapipe_loop, daemon=True)
        self.mp_thread.start()

        # start other logic loop
        self.check_sensor_loop()

        # --- Handle close ---
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # --- Functions ---
    def play_sounds_sequential(self, filename):
        def _play(f=filename):
            try:
                if not f.endswith(".mp3"):
                    f += ".mp3"
                sound_path = f"Voices/{f}"
                sound = pygame.mixer.Sound(sound_path)
                sound.play()
            except Exception as e:
                print(f"Sound error: {e}")
        threading.Thread(target=_play, daemon=True).start()

    def load_history(self):
        try:
            with open("Anti-Finger.txt", "r", encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = ["No history found.\n"]
        max_lines = 13
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        self.history_textbox.configure(state="normal")
        self.history_textbox.delete("1.0", "end")
        self.history_textbox.insert("end", "".join(lines))
        self.history_textbox.see("end")
        self.history_textbox.configure(state="disabled")
        self.after(2000, self.load_history)

    def show_main_page(self):
        self.history_page.pack_forget()
        self.main_content_frame.pack(side="top", fill="both", expand=True, pady=20)
        self.play_sounds_sequential("010.mp3")

    def show_history_page(self):
        self.main_content_frame.pack_forget()
        self.play_sounds_sequential("009.mp3")
        self.history_page.pack(side="top", fill="both", expand=True, pady=20)
        self.load_history()

    def write_log(self, message):
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{now} เซ็ตที่ {self.set} ครั้งที่ {self.round} : {message}"
        with open("Anti-Finger.txt", "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
        print(log_message)

    # --- Camera finger detection ---
    def check_fingers(self):
        ret, frame = self.cap.read()
        if not ret:
            print("[Debug] Failed to grab frame")
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
        white_pixels = cv2.countNonZero(thresh)
        print(f"[Debug] White pixels: {white_pixels}")

        # Dummy pose logic
        if white_pixels > 50000:
            if self.hand_posit < 5:
                self.hand_posit += 1
                self.update_pic()

    # --- Background MediaPipe processing ---
    def _mediapipe_loop(self):
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        drawing_spec_landmark = mp_drawing.DrawingSpec(color=(0,255,0), thickness=2, circle_radius=4)
        drawing_spec_connection = mp_drawing.DrawingSpec(color=(255,0,0), thickness=2, circle_radius=2)

        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # pose requirements per finger: (thumb, index, middle, ring, pinky)
        pose_ranges = {
            1: [(0,200),(150,185),(150,185),(150,185),(150,185)],
            2: [(0,200),(40,160), (40,160),(40,160),(40,160)],
            3: [(0,200),(0,60),(0,60),(0,60),(0,60)],
            4: [(0,200),(0,60),(0,60),(0,60),(0,60)],
            5: [(0,200),(50,130),(50,130),(50,130),(50,130)],
        }

        def _angle_between(a, b):
            import math
            ax, ay = a
            bx, by = b
            dot = ax*bx + ay*by
            na = (ax*ax + ay*ay) ** 0.5
            nb = (bx*bx + by*by) ** 0.5
            if na == 0 or nb == 0:
                return 0.0
            cosv = max(-1.0, min(1.0, dot/(na*nb)))
            return math.degrees(math.acos(cosv))

        try:
            while self.mp_running:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.01)
                    continue
                # flip for mirror view
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]

                # convert to RGB for MediaPipe
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                # default angles
                thumb_a = index_a = middle_a = ring_a = pinky_a = None
                pose_match = False

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            drawing_spec_landmark,
                            drawing_spec_connection
                        )

                        lm = hand_landmarks.landmark
                        def to_pt(idx):
                            return (lm[idx].x * w, lm[idx].y * h)

                        wrist = to_pt(0)

                        # Thumb: mcp=2, tip=4
                        thumb_mcp = to_pt(2); thumb_tip = to_pt(4)
                        v1 = (thumb_tip[0]-thumb_mcp[0], thumb_tip[1]-thumb_mcp[1])
                        v2 = (wrist[0]-thumb_mcp[0], wrist[1]-thumb_mcp[1])
                        thumb_a = _angle_between(v1, v2)

                        # Index: mcp=5 tip=8
                        idx_mcp = to_pt(5); idx_tip = to_pt(8)
                        v1 = (idx_tip[0]-idx_mcp[0], idx_tip[1]-idx_mcp[1])
                        v2 = (wrist[0]-idx_mcp[0], wrist[1]-idx_mcp[1])
                        index_a = _angle_between(v1, v2)

                        # Middle: mcp=9 tip=12
                        mid_mcp = to_pt(9); mid_tip = to_pt(12)
                        v1 = (mid_tip[0]-mid_mcp[0], mid_tip[1]-mid_mcp[1])
                        v2 = (wrist[0]-mid_mcp[0], wrist[1]-mid_mcp[1])
                        middle_a = _angle_between(v1, v2)

                        # Ring: mcp=13 tip=16
                        ring_mcp = to_pt(13); ring_tip = to_pt(16)
                        v1 = (ring_tip[0]-ring_mcp[0], ring_tip[1]-ring_mcp[1])
                        v2 = (wrist[0]-ring_mcp[0], wrist[1]-ring_mcp[1])
                        ring_a = _angle_between(v1, v2)

                        # Pinky: mcp=17 tip=20
                        pinky_mcp = to_pt(17); pinky_tip = to_pt(20)
                        v1 = (pinky_tip[0]-pinky_mcp[0], pinky_tip[1]-pinky_mcp[1])
                        v2 = (wrist[0]-pinky_mcp[0], wrist[1]-pinky_mcp[1])
                        pinky_a = _angle_between(v1, v2)

                        # Check pose ranges for current pose
                        reqs = pose_ranges.get(self.current_pose, pose_ranges[1])
                        angles = [thumb_a, index_a, middle_a, ring_a, pinky_a]
                        ok = True
                        for ang, (mn, mx) in zip(angles, reqs):
                            if ang is None:
                                ok = False
                                break
                            if not (mn <= ang <= mx):
                                ok = False
                                break
                        pose_match = ok

                        # overlay per-finger angles and status
                        try:
                            cv2.putText(frame, f"Match:{'YES' if pose_match else 'NO'}", (10,180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,200,0) if pose_match else (0,0,200), 2)
                        except Exception:
                            pass

                # convert for PIL (BGR -> RGB)
                display_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(display_rgb)
                pil_img = pil_img.resize((self.camera_width, self.camera_height), Image.LANCZOS)

                # schedule update on main thread: update camera image and apply detection result
                try:
                    # send all five angles and match flag
                    self.after(0, lambda im=pil_img, a=(thumb_a, index_a, middle_a, ring_a, pinky_a), m=pose_match: (self._update_camera_label(im), self._apply_pose_detection(a, m)))
                except RuntimeError:
                    break

                time.sleep(0.02)
        finally:
            hands.close()

    def _apply_pose_detection(self, angles, match):
        # Runs on main thread: update hand_posit based on detection
        try:
            if match:
                if self.hand_posit < 5:
                    self.hand_posit += 1
            else:
                self.hand_posit = 0
        except Exception as e:
            print(f"[Pose Apply] {e}")

    def _update_camera_label(self, pil_image):
        # must run on main thread
        try:
            self.camera_photo = ImageTk.PhotoImage(pil_image)
            self.camera_label.configure(image=self.camera_photo)
        except Exception as e:
            print(f"[Camera Update] {e}")

    # --- UI Update Functions ---
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
            l = self.timer_pad; r = self.timer_canvas_size - self.timer_pad
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
                l = self.timer_pad; r = self.timer_canvas_size - self.timer_pad
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
            l = self.timer_pad; r = self.timer_canvas_size - self.timer_pad
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

    # --- Control functions ---
    def toggle_start_pause(self):
        # start countdown and play sounds, or stop/cancel
        if self.start_stop_button.cget("text") == "เริ่มต้น":
            self.start_stop_button.configure(text="หยุด", fg_color=self.yellow_btn, hover_color=self.hover_yellow_bt)
            # start 2s pose countdown
            self.start_pose_countdown(2)
            self.play_sounds_sequential("006.mp3")
            if self.current_pose == 1:
                try:
                    self.after(1500, lambda: self.play_sounds_sequential(self.pose_sounds[self.current_pose][0]))
                except Exception:
                    pass
        else:
            # stop / cancel
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
                l = self.timer_pad; r = self.timer_canvas_size - self.timer_pad
                self.timer_canvas.create_oval(l, l, r, r, outline="#3CB371", width=10, tags="progress")
            except Exception:
                pass

        frac = max(0.0, min(1.0, remaining / float(self.countdown_total)))
        extent = 360 * frac

        # draw smooth clockwise countdown
        try:
            self.timer_canvas.delete("progress")
            l = self.timer_pad; r = self.timer_canvas_size - self.timer_pad
            self.timer_canvas.create_arc(l, l, r, r, start=-90, extent=-extent, style="arc", width=10, outline="#FFA500", tags="progress")
            secs = int(math.ceil(remaining))
            self.timer_canvas.itemconfig(self.timer_text, text=str(secs))
        except Exception:
            pass

        # schedule next animation frame (~50ms)
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
                l = self.timer_pad; r = self.timer_canvas_size - self.timer_pad
                self.timer_canvas.create_oval(l, l, r, r, outline="#3CB371", width=10, tags="progress")
            except Exception:
                pass

    def reset_action(self):
        self.running = False
        self.start_stop_button.configure(text="เริ่มต้น", fg_color=self.green_btn, hover_color=self.hover_green_bt)
        self.round = 0
        self.set = 0
        self.current_pose = 1
        self.timer_reset()
        self.update_text()
        self.update_round()

    def on_close(self):
        self.mp_running = False
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

    # <-- SENSER LOOP -->
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

        # always reschedule
        try:
            self.after(1000, self.check_sensor_loop)
        except Exception as e:
            print(f"[check_sensor_loop] scheduling error: {e}")

    def _on_pose_success(self):
        try:
            if self.time_current > 0:
                return
            self.write_log(f"ท่า{self.pose_name[self.current_pose]}สําเร็จ!")
        except Exception as e:
            print(f"[_on_pose_success] write_log error: {e}")

        # advance pose/rounds
        self.current_pose += 1
        if self.current_pose > 5:
            self.current_pose = 1
            self.round += 1
            if self.round >= 10:
                self.round = 0
                self.set += 1

        # update UI and reset timer
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
