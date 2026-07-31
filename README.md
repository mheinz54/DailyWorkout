# 🏋️‍♂️ Daily 15-Minute Stability Workout System

A localized, secure lower-body, core, and posture tracking system optimized for macOS. This utility manages an automated physical therapy and posture routine, launches interactive tracking templates inside Visual Studio Code, and logs raw exercise completion metrics cleanly into a local SQLite database.

## 📂 Project Architecture
```text
DailyWorkout/
│
├── README.md                 # Project configuration & deployment guide
├── workout.py                # Core Python orchestration engine
├── .gitignore                # Restricts binary DB pushes to Git
├── workout_progress.db       # Local SQLite tracking database (auto-generated)
│
├── Ankle_Knee_Routine.md     # Monday Workout Template
├── Core_Glute_Routine.md     # Tuesday Workout Template
├── Back_Shoulders_Routine.md # Thursday Workout Template
├── Chest_Hamstrings_Routine.md # Friday Workout Template
│
└── images/                   # Local folder containing step-by-step imagery
```

---

## ⚙️ Requirements & Core Configuration
* **Operating System:** macOS (Catalina or higher)
* **Text Editor:** Visual Studio Code (set as default for markdown previewing)
* **Python Runtime:** Python 3 (built natively into macOS command-line tools)

### Verify File Path Execution
To guarantee absolute path compatibility for system automations, ensure this repository lives inside your local Documents index at:
`~/Documents/DailyWorkout/`

---

## 🚀 Step-by-Step Native macOS Automation (`launchd`)

To have this routine automatically pop up every weekday without keeping any terminal windows open, configure the built-in macOS `launchd` manager.

### Step 1: Create the Automation Profile Plist
Open your Mac **Terminal** application and execute the following command to spin up a native configuration profile:
```bash
nano ~/Library/LaunchAgents/com.user.workout.plist
```

### Step 2: Inject the Configuration Script
Paste the following complete XML markup directly into your open terminal editor. 

*Note: If your Mac profile username is not `yourusername`, modify the absolute paths in the `<array>` parameters below to match your machine's exact directory.*

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://apple.com">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.workout</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/yourusername/Documents/DailyWorkout/workout.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
        <dict>
            <key>Hour</key>
            <integer>17</integer> <!-- 5:00 PM System Activation Time (24h format) -->
            <key>Minute</key>
            <integer>00</integer>
        </dict>
    </array>
    <key>StandardOutPath</key>
    <string>/tmp/workout.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/workout.stderr.log</string>
</dict>
</plist>
```
*Save and close the editor by hitting `Control + O`, `Enter`, and then `Control + X`.*

### Step 3: Register and Load the Script to the OS
To load this profile into your active macOS user session background execution threads, run:
```bash
launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/com.user.workout.plist
```

### Step 4: Grant System Permissions
When the script runs automatically for the first time, macOS will display a security banner requesting permissions to allow Terminal or Python to utilize **System Events**. Click **Allow** or navigate manually to *System Settings > Privacy & Security > Automation* to permit script triggers.

---

## 🛠️ Management & Diagnostics

### Manual Execution Testing
If you ever want to launch the tool instantly outside of your scheduled daily alert hour, execute the script natively via your terminal:
```bash
python3 ~/Documents/DailyWorkout/workout.py
```

### Review Progress Reports Direct from SQLite
Your records are stored securely on your local hard drive. To quickly check your raw data tables directly from the command-line interface, query the local database:
```bash
sqlite3 ~/Documents/DailyWorkout/workout_progress.db "SELECT date, routine_name, completed_exercises FROM history ORDER BY date DESC;"
```

### Unloading / Pausing the Automation Schedule
If you go on vacation or wish to temporarily disable the automation pop-up triggers, run this command to unload it from system memory:
```bash
launchctl bootout gui/\$(id -u) ~/Library/LaunchAgents/com.user.workout.plist
```

