# Anti-Finger with Raspberry Pi 4 and Python

## Overview
This Python program is a Tkinter-based GUI application called **"AI-Powered Anti-trigger Fingers"**, designed to monitor finger positions using an **MCP3008 ADC** and provide visual and audio feedback based on hand gestures. It uses **CustomTkinter** for a modern UI, **Pillow** for image handling, **pygame** for sound playback, and **threading** to avoid blocking the UI.

---

## Main Components

### 1. Imports
- `PIL.Image, ImageTk` >>> For loading and resizing images.
- `customtkinter as ctk` >>> Modernized Tkinter UI.
- `threading` >>> Run tasks like playing sound in the background.
- `Adafruit_GPIO.SPI & Adafruit_MCP3008` >>> Read analog sensor values from the MCP3008 ADC.
- `pygame` >>> Play mp3 sound files.
- `playsound` >>> Alternative sound library (though mostly using pygame here).
- `time & datetime` >>> Timing and logging purposes.

---

### 2. Class: `AntiTriggerFingersApp`
The main application class, inheriting from `ctk.CTk`.

#### **Key Sections:**

**Initialization (`__init__`)**
- Window Setup: Fullscreen, fixed size, ESC to exit, white background.
- State Variables:
  - `current_pose` >>> Current hand gesture (1-5)
  - `round & set` >>> Track repetitions
  - `time_current, time_max` >>> Timer for each pose
  - `hand_posit` >>> Step of hand holding in the current pose
- Pose Names >>> Thai names for each pose
- MCP3008 Initialization >>> SPI setup to read sensors
- UI Colors and Fonts >>> Predefined for consistency

**UI Components**
- **Top Bar**
  - Logo (with placeholder if missing)
  - App title
- **Main Content Frame**
  - Left Column >>> Large robot hand image (current pose)
  - Middle Column >>> Round & set counters, pose name & description, start/pause and reset buttons
  - Right Column >>> Timer circle and small pose image (reference hand)
- **History Page**
  - Textbox showing logs from a text file (`Anti-Finger.txt`)
  - Back button to return to the main page

**Sound Handling**
- `play_sounds_sequential(filename)` >>> Plays a sound in a separate thread to avoid blocking the GUI
- `pose_sounds` dictionary >>> Maps poses to their corresponding mp3 files (`001.mp3` to `005.mp3`)

**Sensor Reading**
- `check_fingers()` >>> Reads MCP3008 values and prints them for debugging
- `gestures` >>> Defines acceptable ranges for each pose for all five fingers

**Timer & UI Updates**
- `timer_reset()` >>> Reset hand position and timer to default
- `update_timer()` >>> Draws a circular timer on the canvas
- `update_pic()` >>> Updates large robot hand image based on current pose and step
- `update_EX_pose()` >>> Updates small reference hand image based on the current pose
- `update_text()` >>> Updates pose labels
- Countdown Before Starting: `start_pose_countdown(count=2)` >>> Waits 2 seconds before starting the monitoring loop

**Sensor Monitoring Loop**
- `check_sensor_loop()` >>> Runs repeatedly if `self.running` is `True`
  - Checks if current finger positions match the current pose
  - Updates `hand_posit` gradually
  - Decreases timer if hand is held correctly
  - Logs completion and moves to the next pose
  - Plays the corresponding pose sound

**Buttons**
- `toggle_start_pause()` >>> Starts or pauses the exercise sequence. Plays a general start sound (`006.mp3`) and, if `current_pose == 1`, plays the first pose sound (`001.mp3`) after a short delay
- `reset_action()` >>> Resets rounds, sets, hand positions, timer, images, and buttons. Plays a reset sound (`008.mp3`)

**History Logging**
- `write_log(message)` >>> Appends timestamped messages to `Anti-Finger.txt`
- `load_history()` >>> Loads the last 13 lines into the history textbox
- `show_history_page()` / `show_main_page()` >>> Switch between main screen and history page

---

### 3. Miscellaneous
- `create_dummy_images()` >>> Generates placeholder images if real images are missing. Useful for testing the UI.

---

### 4. Main Execution
```python
if __name__ == "__main__":
    create_dummy_images()
    app = AntiTriggerFingersApp()
    app.mainloop() 
```


### Functionality Summary
1. The app displays a robot hand and reference images for finger exercises.
2. Reads finger positions via MCP3008 sensors.
3. Tracks rounds, sets, and pose completion.
4. Provides visual feedback (images & timer) and audio feedback (pose sounds, start/pause/reset).
5. Logs completed poses with timestamps.
6. Supports history viewing in a separate page.

---

### Thank You
**Tayakorn000** and **Achidesu (OWNER)**



