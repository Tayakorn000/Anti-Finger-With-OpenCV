import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from collections import defaultdict
import os

FILE_PATH = "Anti-Finger.txt"

def get_history_from_file():
    daily_counts = defaultdict(int)
    if not os.path.exists(FILE_PATH):
        return []

    # อ่านไฟล์และนับจำนวนครั้งต่อวัน
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            try:
                date_str = line.split("]")[0][1:]
                date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                daily_counts[date.date()] += 1
            except:
                continue

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

class ProgressChart:
    def __init__(self, parent, get_history_func):
        self.parent = parent
        self.get_history_func = get_history_func

        # Main frame
        self.main_frame = tk.Frame(parent)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Chart frame
        self.chart_frame = tk.Frame(self.main_frame)
        self.chart_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Control frame (right)
        self.control_frame = tk.Frame(self.main_frame)
        self.control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, pady=10)

        # Dropdown เลือกวัน
        tk.Label(self.control_frame, text="Select Date:").pack(anchor='w')
        self.date_var = tk.StringVar()
        self.date_combo = ttk.Combobox(self.control_frame, textvariable=self.date_var, width=12)
        self.date_combo.pack(anchor='w')
        self.date_combo.bind("<<ComboboxSelected>>", lambda e: self.update_feedback())

        # Legend
        tk.Label(self.control_frame, text="\nLegend / สี Progress", font=("Arial",10,"bold")).pack(anchor='w')
        tk.Label(self.control_frame, text="แดง: <50%", fg="red").pack(anchor='w')
        tk.Label(self.control_frame, text="เขียว: ≥50% / ดีขึ้น ↑", fg="green").pack(anchor='w')
        tk.Label(self.control_frame, text="เหลือง / แย่ลง ↓", fg="orange").pack(anchor='w')
        tk.Label(self.control_frame, text="\nClick dot for feedback", font=("Arial",9)).pack(anchor='w')

        # Feedback label
        self.feedback_label = tk.Label(self.control_frame, text="", bg="lightyellow", justify='left', wraplength=200)
        self.feedback_label.pack(fill='x', pady=10)

        # Figure and canvas
        self.fig, self.ax = plt.subplots(figsize=(8,4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.canvas.mpl_connect("button_press_event", self.on_click)

        # ดึงข้อมูลและสร้าง combo วัน
        self.history = self.get_history_func()
        self.populate_date_combo()
        self.draw_chart()

    def populate_date_combo(self):
        dates = [h['date'].strftime('%d-%b-%Y') for h in self.history]
        self.date_combo['values'] = dates
        if dates:
            self.date_var.set(dates[-1])  # เลือกวันล่าสุดเป็น default

    def progress_color(self, prog, prev_prog):
        """กำหนดสีตามการเปรียบเทียบกับวันก่อนหน้า"""
        if prev_prog is None:
            return (1,0,0) if prog < 50 else (0,1,0)  # แดงหรือเขียวตามปกติ
        if prog > prev_prog:
            return (0,1,0)  # เขียว = ดีขึ้น
        elif prog < prev_prog:
            return (1,0.65,0)  # เหลือง = ลดลง
        else:
            return (1,0,0) if prog < 50 else (0,1,0)  # แดง/เขียวตามปกติ

    def feedback_text(self, prog, prev_prog):
        if prog == 0:
            return "วันนี้คุณยังไม่ได้ทำ"
        elif prev_prog is not None and prog < prev_prog:
            return "วันนี้คุณทำได้น้อยลง"
        elif prev_prog is not None and prog > prev_prog:
            return "วันนี้คุณทำได้ดีขึ้น"
        elif prog < 50:
            return "วันนี้คุณทำได้น้อย"
        else:
            return "วันนี้คุณทำได้ตามปกติ"

    def draw_chart(self):
        self.dates = [h['date'] for h in self.history]
        self.progresses = [h['progress'] for h in self.history]
        self.sets_done = [h['sets_done'] for h in self.history]

        o, h_, l, c = [], [], [], []
        prev = self.progresses[0] if self.progresses else 0
        self.points = []
        for i, p in enumerate(self.progresses):
            o.append(prev)
            c.append(p)
            high = max(prev,p)
            low = min(prev,p)
            h_.append(high)
            l.append(low)
            prev = p

        self.ax.clear()
        for i, p in enumerate(self.progresses):
            prev_prog = self.progresses[i-1] if i > 0 else None
            color = self.progress_color(p, prev_prog)
            self.ax.vlines(self.dates[i], l[i], h_[i], color=color, linewidth=2)
            self.ax.vlines(self.dates[i], o[i], c[i], color=color, linewidth=8)
            # ลูกศร
            if prev_prog is not None:
                if p > prev_prog:
                    self.ax.annotate('↑', xy=(self.dates[i], c[i]+3), ha='center', color='green', fontsize=12)
                elif p < prev_prog:
                    self.ax.annotate('↓', xy=(self.dates[i], c[i]+3), ha='center', color='orange', fontsize=12)
            point, = self.ax.plot(self.dates[i], c[i], 'o', color='black', picker=5)
            self.points.append((point, self.dates[i], p, self.sets_done[i], i))

        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%d-%b'))
        self.ax.set_ylabel("Progress (%)")
        self.ax.set_ylim(0,110)
        self.ax.set_title("Progress Chart")
        self.ax.grid(True, linestyle='--', alpha=0.5)
        self.fig.autofmt_xdate()
        self.canvas.draw()

        self.update_feedback()

    def update_feedback(self):
        selected_date_str = self.date_var.get()
        if not selected_date_str:
            return
        selected_date = datetime.strptime(selected_date_str, '%d-%b-%Y').date()
        idx = next((i for i, h in enumerate(self.history) if h['date'].date() == selected_date), None)
        if idx is None:
            return
        prog = self.history[idx]['progress']
        sets = self.history[idx]['sets_done']
        prev_prog = self.history[idx-1]['progress'] if idx > 0 else None
        feedback = self.feedback_text(prog, prev_prog)
        self.feedback_label.config(text=f"{selected_date_str}\nProgress: {prog:.0f}%\nSets: {sets}\n{feedback}")

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        for point, date, prog, sets, idx in self.points:
            xdata = mdates.date2num(date)
            ydata = prog
            if abs(event.xdata - xdata) < 0.3 and abs(event.ydata - ydata) < 5:
                prev_prog = self.progresses[idx-1] if idx > 0 else None
                feedback = self.feedback_text(prog, prev_prog)
                self.feedback_label.config(text=f"{date.strftime('%d-%b-%Y')}\nProgress: {prog:.0f}%\nSets: {sets}\n{feedback}")
                return

if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.geometry("1000x450")
        root.title("Progress Chart with Up/Down Arrows")
        chart = ProgressChart(root, get_history_from_file)
        root.mainloop()
    except Exception as e:
        print("Error:", e)
        messagebox.showerror("Error", str(e))
