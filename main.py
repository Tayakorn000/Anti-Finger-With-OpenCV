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
from PIL import Image, ImageTk           # Image processing + Tkinter bridge
import customtkinter as ctk              # Modern Tkinter look-and-feel
import cv2                               # OpenCV for camera I/O and image ops
import mediapipe as mp                   # MediaPipe Hands: landmark detector
import pygame                            # For playing short sound cues
import time, threading                   # Threading for background loops, time helpers
from datetime import datetime            # Timestamps for logging
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
        self.overrideredirect(True)                 # hide window frame for kiosk style
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
            "งอโคนนิ้วแต่เหยียดปลายนิ้วมือ"
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
                self.top_bar_frame, text="LOGO", font=("Sarabun", 20), fg=self.white_fg, bg=self.purple_bg
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
        self.history_title.pack(pady=20)
        self.history_textbox = ctk.CTkTextbox(self.history_page, width=1000, height=500, font=("Sarabun", 20), text_color=self.black_fg, fg_color="#CCC9C9")
        self.history_textbox.pack(padx=40, pady=20)
        self.history_footer = ctk.CTkFrame(self.history_page, fg_color=self.light_gray_bg_program)
        self.history_footer.pack(fill="x", padx=40, pady=(0, 20))
        self.back_button = ctk.CTkButton(
            self.history_footer,
            text="กลับ",
            font=("Sarabun", 40, "bold"),
            fg_color="#FF9800",
            text_color="white",
            hover_color="#E68900",
            command=lambda: self.show_main_page(),
            height=80,
            width=260,
        )
        self.back_button.pack(side="right", padx=140, pady=10)

        # --------------------------------------------------------------------
        # Sound setup (pygame mixer)
        # --------------------------------------------------------------------
        # Short sounds are played by play_sounds_sequential. If mixer init
        # fails, the program continues but sound won't play.
        self.pose_sounds = {1: ["001.mp3"], 2: ["002.mp3"], 3: ["003.mp3"], 4: ["004.mp3"], 5: ["005.mp3"]}
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception as e:
            # Non-fatal: continue without audio
            print(f"[Sound] Pygame mixer init error: {e}")

        # --------------------------------------------------------------------
        # Runtime control flags & countdown state
        # --------------------------------------------------------------------
        self.running = False
        self.countdown_active = False
        self.countdown_job = None
        self.countdown_remaining = 0

        # --------------------------------------------------------------------
        # Start MediaPipe background thread for real-time detection
        # --------------------------------------------------------------------
        # The thread captures frames, runs MediaPipe, draws landmarks, computes
        # finger angles, then schedules UI updates on the main thread using .after.
        self.mp_running = True
        self.mp_thread = threading.Thread(target=self._mediapipe_loop, daemon=True)
        self.mp_thread.start()

        # Start the periodic sensor loop that consumes detection results
        self.check_sensor_loop()

        # Ensure we clean up properly on window close
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ------------------------------
    # PLAY SOUND (THREAD-SAFE)
    # ------------------------------
    def play_sounds_sequential(self, filename):
        """
        Play a short sound file from Voices/ on a daemon thread.
        Keeps UI responsive by not blocking the main thread.
        """
        def _play(f=filename):
            try:
                if not f.endswith(".mp3"):
                    f += ".mp3"
                sound_path = f"Voices/{f}"
                sound = pygame.mixer.Sound(sound_path)
                sound.play()
            except Exception as e:
                # Non-fatal; log for developer.
                print(f"Sound error: {e}")

        threading.Thread(target=_play, daemon=True).start()

    # ------------------------------
    # HISTORY & REPORTING
    # ------------------------------
    def load_history(self):
        """
        Load the last N lines from Anti-Finger.txt and display in the
        history textbox. This function re-schedules itself every 2 seconds
        to keep the view up-to-date while the history page is visible.
        """
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
        # Re-run periodically while history page is shown
        self.after(2000, self.load_history)

    def show_main_page(self):
        """
        Return to main UI from history page and play a small audio cue.
        """
        self.history_page.pack_forget()
        self.main_content_frame.pack(side="top", fill="both", expand=True, pady=20)
        self.play_sounds_sequential("010.mp3")

    def show_history_page(self):
        """
        Switch to history page and begin refreshing the history view.
        """
        self.main_content_frame.pack_forget()
        self.play_sounds_sequential("009.mp3")
        self.history_page.pack(side="top", fill="both", expand=True, pady=20)
        self.load_history()

    def write_log(self, message):
        """
        Append a single log line to Anti-Finger.txt including a timestamp,
        set/round context, and the provided message.
        """
        now = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_message = f"{now} เซ็ตที่ {self.set} ครั้งที่ {self.round} : {message}"
        with open("Anti-Finger.txt", "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
        print(log_message)

    # ------------------------------
    # SIMPLE CAMERA-BASED FALLBACK CHECK
    # ------------------------------
    def check_fingers(self):
        """
        A simple (fallback / legacy) detector that thresholds the grayscale frame
        and counts white pixels. This function is still called by the sensor loop
        as a lightweight check if you want to use a different metric or debug.
        """
        ret, frame = self.cap.read()
        if not ret:
            print("[Debug] Failed to grab frame")
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)[1]
        white_pixels = cv2.countNonZero(thresh)
        print(f"[Debug] White pixels: {white_pixels}")

        # Very coarse rule: if many white pixels found, increment hand_posit
        if white_pixels > 50000:
            if self.hand_posit < 5:
                self.hand_posit += 1
                # update_pic is a placeholder in the original file (no-op)
                self.update_pic()

    # ------------------------------
    # BACKGROUND: MEDIAPIPE LOOP
    # ------------------------------
    def _mediapipe_loop(self):
        """
        Background thread: continuously read frames from camera, run MediaPipe
        hand detection, compute per-finger angles and pose-match logic,
        draw landmarks on the frame, and schedule UI updates (camera preview
        + pose detection result) on the main thread via .after.

        Important:
          - This thread must never perform UI operations directly.
          - Instead, it prepares a PIL image and calls self.after(0, ...)
            to hand over the image to the main Tk event loop.
        """
        mp_hands = mp.solutions.hands
        mp_drawing = mp.solutions.drawing_utils
        drawing_spec_landmark = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=4)
        drawing_spec_connection = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=2, circle_radius=2)

        # Create a MediaPipe Hands object configured for live detection.
        hands = mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        # --------------------------------------------------------------------
        # Configuration: pose thresholds for each finger per pose index.
        # Each entry is a list of (min_angle, max_angle) for
        # (thumb, index, middle, ring, pinky).
        # --------------------------------------------------------------------
        pose_ranges = {
            1: [(0, 200), (150, 185), (150, 185), (150, 185), (150, 185)],
            2: [(0, 200), (40, 170), (40, 170), (40, 170), (40, 170)],
            3: [(0, 200), (0, 60), (0, 60), (0, 60), (0, 60)],
            4: [(0, 200), (0, 50), (0, 50), (0, 50), (0, 50)],
            5: [(0, 200), (50, 185), (50, 185), (50, 160), (50, 160)],
        }

        def _angle_between(a, b):
            """
            Compute the 2D angle (degrees) between vectors a and b.
            Returns 0.0 if either vector has zero length.
            """
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
                # ----------------
                # Capture frame
                # ----------------
                ret, frame = self.cap.read()
                if not ret:
                    # If capture fails repeatedly, yield CPU and continue
                    time.sleep(0.01)
                    continue

                # Mirror the frame for a natural selfie view
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]

                # Convert to RGB for MediaPipe processing
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                # Initialize angle variables and match flag
                thumb_a = index_a = middle_a = ring_a = pinky_a = None
                pose_match = False

                # If a hand is detected, compute angles and draw landmarks
                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        # Draw landmarks & connections on the BGR frame for debugging/display
                        mp_drawing.draw_landmarks(
                            frame,
                            hand_landmarks,
                            mp_hands.HAND_CONNECTIONS,
                            drawing_spec_landmark,
                            drawing_spec_connection,
                        )

                        lm = hand_landmarks.landmark

                        def to_pt(idx):
                            # Convert normalized landmark coordinates to image pixels
                            return (lm[idx].x * w, lm[idx].y * h)

                        # Use wrist as a common origin for the simple angle test
                        wrist = to_pt(0)

                        # Thumb: compute vector between MCP (2) and tip (4)
                        thumb_mcp = to_pt(2)
                        thumb_tip = to_pt(4)
                        v1 = (thumb_tip[0] - thumb_mcp[0], thumb_tip[1] - thumb_mcp[1])
                        v2 = (wrist[0] - thumb_mcp[0], wrist[1] - thumb_mcp[1])
                        thumb_a = _angle_between(v1, v2)

                        # Index finger (MCP=5, tip=8)
                        idx_mcp = to_pt(5)
                        idx_tip = to_pt(8)
                        v1 = (idx_tip[0] - idx_mcp[0], idx_tip[1] - idx_mcp[1])
                        v2 = (wrist[0] - idx_mcp[0], wrist[1] - idx_mcp[1])
                        index_a = _angle_between(v1, v2)

                        # Middle finger (MCP=9, tip=12)
                        mid_mcp = to_pt(9)
                        mid_tip = to_pt(12)
                        v1 = (mid_tip[0] - mid_mcp[0], mid_tip[1] - mid_mcp[1])
                        v2 = (wrist[0] - mid_mcp[0], wrist[1] - mid_mcp[1])
                        middle_a = _angle_between(v1, v2)

                        # Ring finger (MCP=13, tip=16)
                        ring_mcp = to_pt(13)
                        ring_tip = to_pt(16)
                        v1 = (ring_tip[0] - ring_mcp[0], ring_tip[1] - ring_mcp[1])
                        v2 = (wrist[0] - ring_mcp[0], wrist[1] - ring_mcp[1])
                        ring_a = _angle_between(v1, v2)

                        # Pinky (MCP=17, tip=20)
                        pinky_mcp = to_pt(17)
                        pinky_tip = to_pt(20)
                        v1 = (pinky_tip[0] - pinky_mcp[0], pinky_tip[1] - pinky_mcp[1])
                        v2 = (wrist[0] - pinky_mcp[0], wrist[1] - pinky_mcp[1])
                        pinky_a = _angle_between(v1, v2)

                        # ----------------------------
                        # Pose matching: compare each
                        # finger angle to pose thresholds
                        # ----------------------------
                        reqs = pose_ranges.get(self.current_pose, pose_ranges[1])
                        angles = [thumb_a, index_a, middle_a, ring_a, pinky_a]
                        ok = True
                        for ang, (mn, mx) in zip(angles, reqs):
                            if ang is None:
                                ok = False
                                break
                            # If any finger falls outside the configured range, not matched
                            if not (mn <= ang <= mx):
                                ok = False
                                break
                        pose_match = ok

                        # Overlay small status text on the working frame (debug-friendly)
                        try:
                            cv2.putText(
                                frame,
                                f"Match:{'YES' if pose_match else 'NO'}",
                                (10, 180),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.6,
                                (0, 200, 0) if pose_match else (0, 0, 200),
                                2,
                            )
                        except Exception:
                            # Non-fatal drawing error (different OpenCV builds can vary)
                            pass

                # ----------------------------
                # Convert frame to PIL Image and crop/resize to camera label size
                # ----------------------------
                display_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(display_rgb)

                # Crop-and-resize helper to fill the camera area without letterboxing
                def _crop_and_resize(img, target_w, target_h):
                    src_w, src_h = img.size
                    target_ratio = target_w / target_h
                    src_ratio = src_w / src_h
                    if src_ratio > target_ratio:
                        # image is wider -> crop left/right
                        new_w = int(src_h * target_ratio)
                        left = (src_w - new_w) // 2
                        img = img.crop((left, 0, left + new_w, src_h))
                    else:
                        # image is taller -> crop top/bottom
                        new_h = int(src_w / target_ratio)
                        top = (src_h - new_h) // 2
                        img = img.crop((0, top, src_w, top + new_h))
                    return img.resize((target_w, target_h), Image.LANCZOS)

                pil_img = _crop_and_resize(pil_img, self.camera_width, self.camera_height)

                # Schedule UI update on main thread (safe: using self.after)
                try:
                    # We pass the pil image and the computed angles/match flag
                    self.after(0, lambda im=pil_img, a=(thumb_a, index_a, middle_a, ring_a, pinky_a), m=pose_match: (
                        self._update_camera_label(im),
                        self._apply_pose_detection(a, m)
                    ))
                except RuntimeError:
                    # If the Tk mainloop is shutting down, break out of loop
                    break

                # Small sleep to reduce CPU usage and control frame rate
                time.sleep(0.02)
        finally:
            # Ensure resources are cleaned up when thread ends
            hands.close()

    # ------------------------------
    # APPLY POSE DETECTION RESULT (MAIN THREAD)
    # ------------------------------
    def _apply_pose_detection(self, angles, match):
        """
        Main-thread handler that consumes pose-match boolean from the
        background thread and updates the short-term positive counter
        self.hand_posit which the sensor loop uses to decrement the timer.
        """
        try:
            if match:
                # Use a short hysteresis: require consecutive matches to progress
                if self.hand_posit < 5:
                    self.hand_posit += 1
            else:
                # Reset on mismatch (strict behavior)
                self.hand_posit = 0
        except Exception as e:
            print(f"[Pose Apply] {e}")

    # ------------------------------
    # UPDATE CAMERA LABEL (MAIN THREAD)
    # ------------------------------
    def _update_camera_label(self, pil_image):
        """
        Convert PIL image into a PhotoImage and set it on the camera Label.
        Using self.camera_photo reference prevents garbage collection.
        """
        try:
            self.camera_photo = ImageTk.PhotoImage(pil_image)
            self.camera_label.configure(image=self.camera_photo)
        except Exception as e:
            print(f"[Camera Update] {e}")

    # ------------------------------
    # TIMER & UI UPDATE HELPERS
    # ------------------------------
    def timer_reset(self):
        """
        Reset timer state to initial values for the new pose.
        """
        self.time_current = self.time_max
        self.hand_posit = 0
        self.update_timer()
        self.reset_pic()
        try:
            self.update_EX_pose()
        except Exception:
            pass

    def update_pic(self):
        """
        Placeholder method in original project; kept as no-op to avoid
        changing runtime behavior. Could be used to update a large
        example or camera overlay.
        """
        return

    def reset_pic(self):
        """
        Reset the timer canvas drawing to a neutral circular state.
        """
        self.timer_canvas.delete("progress")
        l = self.timer_pad
        r = self.timer_canvas_size - self.timer_pad
        self.timer_canvas.create_oval(l, l, r, r, outline="#3CB371", width=10, tags="progress")

    def update_timer(self):
        """
        Prepare and start a 1-second smoothing animation for the timer display.
        Uses an interpolated arc update executed by _animate_timer.
        """
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
        """
        Animation loop for a single second of timer interpolation.
        Updates arc extent and central countdown number smoothly.
        """
        try:
            now = time.time()
            elapsed = now - self._timer_anim_start
            t = min(1.0, max(0.0, elapsed / float(self._timer_anim_duration)))
            progress = self._timer_anim_from + (self._timer_anim_to - self._timer_anim_from) * t
            extent = 360 * progress

            self.timer_canvas.delete("progress")
            l = self.timer_pad
            r = self.timer_canvas_size - self.timer_pad
            # Draw arc (clockwise negative extent to create a clockwise progress)
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
                # Continue animation at ~20 FPS
                self.timer_anim_job = self.after(50, self._animate_timer)
            else:
                # Finalize and set static arc for new timer value
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
        """
        Stops any running timer animation and draws the static progress state.
        """
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

    # ------------------------------
    # UI textual updates
    # ------------------------------
    def update_text(self):
        """
        Refresh displayed pose name and index on the main UI.
        """
        self.Label_pose_action_text.configure(text=f"{self.pose_name[self.current_pose]}")
        self.Label_pose_thai_text.configure(text=f"ท่าที่ {self.current_pose}")

    def update_round(self):
        """
        Refresh the displayed round and set counters.
        """
        self.Label_set_times_number.configure(text=f"{self.round}")
        self.Label_set_number.configure(text=f"{self.set}")

    def update_EX_pose(self):
        """
        Update the example pose image on the right panel.
        Silently fails if the file is missing (non-fatal).
        """
        try:
            small_hand_image_pil = Image.open(f"pictures/EX_POSE/pose{self.current_pose}.png")
            small_hand_image_pil = small_hand_image_pil.resize((300, 300))
            self.small_hand_photo = ImageTk.PhotoImage(small_hand_image_pil)
            self.small_hand_label.configure(image=self.small_hand_photo)
        except:
            # Missing file or I/O error; keep previous image
            pass

    # ------------------------------
    # CONTROL: Start / Pause / Countdown
    # ------------------------------
    def toggle_start_pause(self):
        """
        Start or stop the training session:
          - When starting: switch button visuals, run a short countdown, enable running flag
          - When stopping: cancel countdown, disable running flag, play stop sound
        """
        if self.start_stop_button.cget("text") == "เริ่มต้น":
            # Switch to 'Stop' state and begin short countdown
            self.start_stop_button.configure(text="หยุด", fg_color=self.yellow_btn, hover_color=self.hover_yellow_bt)
            self.start_pose_countdown(2)  # 2-second warmup countdown before timer starts decrementing
            self.play_sounds_sequential("006.mp3")
            if self.current_pose == 1:
                try:
                    # Play the pose voice after a short delay for user guidance
                    self.after(1500, lambda: self.play_sounds_sequential(self.pose_sounds[self.current_pose][0]))
                except Exception:
                    pass
        else:
            # Stop / cancel
            self.start_stop_button.configure(text="เริ่มต้น", fg_color=self.green_btn, hover_color=self.hover_green_bt)
            self.running = False
            self._cancel_countdown()
            self.play_sounds_sequential("007.mp3")

    def start_pose_countdown(self, seconds: int):
        """
        Begin a countdown shown on the timer canvas. When the countdown
        completes, sets self.running = True so the sensor loop decrements
        the active pose timer.
        """
        self._cancel_countdown()
        self.countdown_active = True
        self.countdown_total = max(1, seconds)
        self.countdown_end_time = time.time() + self.countdown_total
        self.countdown_job = self.after(0, self._animate_countdown)

    def _animate_countdown(self):
        """
        Smooth visual countdown animation that updates the timer canvas
        every ~50 ms. When countdown finishes, set running=True.
        """
        if not self.countdown_active:
            return
        import math, time as _time
        now = _time.time()
        remaining = self.countdown_end_time - now
        if remaining <= 0:
            # Countdown finished: enable the sensor loop behavior
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

        # Draw clockwise orange countdown arc and numeric seconds remaining
        try:
            self.timer_canvas.delete("progress")
            l = self.timer_pad
            r = self.timer_canvas_size - self.timer_pad
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
        """
        Cancel any active countdown and reset the timer canvas to the
        static initial timer display.
        """
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

    # ------------------------------
    # RESET UI / SESSION
    # ------------------------------
    def reset_action(self):
        """
        Reset the training session to default values and cancel any active
        countdown or running session. Also plays a reset sound.
        """
        # stop activity and cancel any countdowns
        self.running = False
        try:
            self._cancel_countdown()
        except Exception:
            pass

        # reset UI state and counters
        self.start_stop_button.configure(text="เริ่มต้น", fg_color=self.green_btn, hover_color=self.hover_green_bt)
        self.round = 0
        self.set = 0
        self.current_pose = 1
        self.timer_reset()
        self.update_text()
        self.update_round()

        # play reset/main sound (010) if available
        try:
            self.play_sounds_sequential("008.mp3")
        except Exception as e:
            print(f"[reset_action] play sound error: {e}")

    # ------------------------------
    # CLEANUP & EXIT
    # ------------------------------
    def on_close(self):
        """
        Gracefully stop background threads and release camera resource
        before destroying the main window.
        """
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

    # ------------------------------
    # PERIODIC SENSOR LOOP
    # ------------------------------
    def check_sensor_loop(self):
        """
        Periodic loop scheduled on the main thread (via .after).
        If running, it checks the 'hand_posit' counter and decrements the
        pose timer (time_current) when hand_posit indicates a stable match.
        When the timer reaches zero, schedule _on_pose_success.
        This loop re-schedules itself every 1 second.
        """
        if self.running:
            try:
                # Lightweight fallback / debug detector
                self.check_fingers()
            except Exception as e:
                print(f"[check_sensor_loop] check_fingers error: {e}")

            # If we have consistent positive detections, decrement the timer
            if self.hand_posit == 5 and self.time_current > 0 and not self.still_hold:
                try:
                    self.time_current -= 1
                    self.update_timer()
                except Exception as e:
                    print(f"[check_sensor_loop] timer update error: {e}")

                if self.time_current <= 0:
                    try:
                        delay_ms = int(getattr(self, "_timer_anim_duration", 1.0) * 1000) + 50
                        # Allow animation to finish, then call success handler
                        self.after(delay_ms, self._on_pose_success)
                    except Exception as e:
                        print(f"[check_sensor_loop] scheduling _on_pose_success error: {e}")

        # always reschedule the sensor loop (1-second cadence)
        try:
            self.after(1000, self.check_sensor_loop)
        except Exception as e:
            print(f"[check_sensor_loop] scheduling error: {e}")

    # ------------------------------
    # POSE SUCCESS / ADVANCE LOGIC
    # ------------------------------
    def _on_pose_success(self):
        """
        Called when the user successfully holds the current pose for the
        required duration. Writes to history, advances pose/round counters,
        updates UI, and plays the next pose sound if available.
        """
        try:
            if self.time_current > 0:
                # Spurious call guard
                return
            self.write_log(f"ท่า{self.pose_name[self.current_pose]}สําเร็จ!")
        except Exception as e:
            print(f"[_on_pose_success] write_log error: {e}")

        # Advance to next pose. Wrap-around after pose 5 and advance round/set counters.
        self.current_pose += 1
        if self.current_pose > 5:
            self.current_pose = 1
            self.round += 1
            if self.round >= 10:
                # After completing 10 rounds, increment set count and reset round
                self.round = 0
                self.set += 1

        # Update UI and prepare the timer for the next pose
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
