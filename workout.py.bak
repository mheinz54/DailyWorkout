import os
import sqlite3
import datetime
import subprocess
import sys
import time

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "workout_progress.db")

ROUTINES = {
    1: {"title": "Ankle_Knee_Routine", "exercises": ["Flat-Ground Straight-Knee Calf Raises", "Short Foot Isometric Holds", "Wall Sit with Pillow Squeeze", "Backward Step-Downs", "Side-Lying Inner Thigh Lifts", "Plie Squat Isometrics"]},
    2: {"title": "Core_Glute_Routine", "exercises": ["Deadbug", "Forearm Plank with Toe Taps", "Side Plank with Isometric Clamshell", "Bird-Dog", "Single-Leg Glute Bridge Iso-Hold", "Donkey Kick to Fire Hydrant Combo"]},
    3: {"title": "Rest_Day", "exercises": []},
    4: {"title": "Back_Shoulders_Routine", "exercises": ["Band Pull-Aparts", "Prone Dumbbell Y Raises", "Barbell Bent-Over Rows", "Heavy Dumbbell Farmer Carries", "Barbell Overhead Strict Press", "Banded Scapular Wall Slides"]},
    5: {"title": "Chest_Hamstrings_Routine", "exercises": ["Standard Floor Push-Ups", "Dumbbell Romanian Deadlifts", "Floor Dumbbell Chest Press", "Yoga Mat Hamstring Walkouts", "Plank-to-Push-Up Hold"]}
}

def setup_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            routine_name TEXT,
            completed_exercises TEXT
        )
    ''')
    conn.commit()
    conn.close()

def send_mac_notification(title, message):
    # Uses standard user notifications instead of interrupting dialogs
    applescript = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", applescript])

def prompt_user_action(message, buttons=["View Workout", "See Progress Logs", "Skip"]):
    buttons_str = ", ".join([f'"{b}"' for b in buttons])
    
    # Core Fix: Using standard 'display dialog' without packing it inside 'tell application "System Events"'
    # This prevents macOS from triggering privacy access violations in Terminal
    applescript = f'display dialog "{message}" with title "🏋️‍♂️ Daily Workout Reminder" buttons {{{buttons_str}}} default button "View Workout"'
    
    print(f"[Debug] Launching popup: {message}")
    try:
        process = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, check=True)
        result = process.stdout.strip()
        print(f"[Debug] Popup raw response: {result}")
        
        # Check standard AppleScript output formats safely
        for b in buttons:
            if b in result:
                return b
    except subprocess.CalledProcessError as e:
        print(f"[Debug] Popup was dismissed or errored. Error details:\n{e.stderr}")
        return "Skip"
    return "Skip"

def open_markdown(day_num):
    routine = ROUTINES[day_num]
    filename = f"{routine['title']}.md"
    filepath = os.path.join(BASE_DIR, filename)
    print(f"[Debug] Attempting to open file: {filepath}")
    if os.path.exists(filepath):
        subprocess.run(["open", filepath])
    else:
        print(f"[Error] File not found: {filepath}")
        send_mac_notification("Error", f"Could not find {filename}")

def log_completion_gui(day_num):
    routine = ROUTINES[day_num]
    today_str = datetime.date.today().isoformat()
    completed = []
    
    print("[Debug] Starting exercise checklist loop...")
    for exe in routine['exercises']:
        applescript = f'display dialog "Did you complete:\\n\\n{exe}?" buttons {{"No", "Yes"}} default button "Yes"'
        try:
            process = subprocess.run(["osascript", "-e", applescript], capture_output=True, text=True, check=True)
            res = process.stdout.strip()
            if "Yes" in res:
                completed.append(exe)
        except subprocess.CalledProcessError:
            print(f"[Debug] Skipped exercise or clicked No: {exe}")
            
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO history (date, routine_name, completed_exercises)
        VALUES (?, ?, ?)
    ''', (today_str, routine['title'], ", ".join(completed)))
    conn.commit()
    conn.close()
    print(f"[Debug] Progress recorded to DB: {len(completed)} exercises done.")
    send_mac_notification("Workout Saved!", f"Logged {len(completed)} exercises successfully.")

def show_progress_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT date, routine_name, completed_exercises FROM history ORDER BY date DESC LIMIT 7")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        summary = "No workout logs found yet."
    else:
        summary = "📋 YOUR RECENT WORKOUT HISTORY:\\n\\n"
        for row in rows:
            clean_title = row[1].replace('_',' ')
            summary += f"📅 {row[0]} | {clean_title}\\n"
            summary += f"✅ Done: {row[2][:50] if row[2] else 'None'}\\n\\n"
            
    applescript = f'display dialog "{summary}" buttons {{"Close"}} default button "Close" with title "Workout History Logs"'
    subprocess.run(["osascript", "-e", applescript])

def main():
    setup_database()
    weekday = datetime.datetime.today().isoweekday()
    print(f"[Debug] Script running. Current Day-of-week ID: {weekday} (Mon=1, Fri=5)")
    
    if weekday > 5:
        print("[Debug] Weekend detected. Exiting.")
        send_mac_notification("Weekend", "Enjoy your weekend rest!")
        return

    if weekday == 3:
        print("[Debug] Wednesday Rest Day detected.")
        action = prompt_user_action("Today is your designated REST DAY. Take care of your joints!", ["See Progress Logs", "Close"])
        if action == "See Progress Logs":
            show_progress_history()
        return

    routine_name = ROUTINES[weekday]["title"].replace('_', ' ')
    action = prompt_user_action(f"Time to move! Today's session: {routine_name}.")
    print(f"[Debug] Action chosen by user: {action}")
    
    if action == "View Workout":
        open_markdown(weekday)
        
        print("[System] Markdown document opened. Starting your 15-minute training session...")
        send_mac_notification("Workout Started", "Your 15-minute timer has begun. Follow along in VS Code!")
        
        workout_duration_seconds = 900  # 15 minutes
        
        for remaining in range(workout_duration_seconds, 0, -1):
            sys.stdout.write(f"\r⏱️ Workout Time Remaining: {remaining // 60:02d}:{remaining % 60:02d}")
            sys.stdout.flush()
            time.sleep(1)
        print("\n[System] Time is up!")
        
        # Force the Terminal window to the front to catch your attention
        subprocess.run(['osascript', '-e', 'tell application "Terminal" to activate'], capture_output=True)
        time.sleep(0.5)
        
        # Audio alert to tell you the session is over
        subprocess.run(['osascript', '-e', 'beep 2'], capture_output=True)
        send_mac_notification("Time's Up!", "Great job! Look at your Terminal window to log progress.")
        
        # --- FOOLPROOF FIX: TERMINAL INPUT ---
        print("\n" + "="*50)
        print("🎉 GREAT WORKOUT SESSION!")
        print("="*50)
        choice = input("Ready to log your progress? (Press Enter to start logging, or type 'n' to cancel): ").strip().lower()
        
        if choice in ['', 'y', 'yes', 'log']:
            log_completion_gui(weekday)
        else:
            print("[Debug] Logging phase canceled by user via Terminal command.")
            
    elif action == "See Progress Logs":
        show_progress_history()





if __name__ == "__main__":
    main()
