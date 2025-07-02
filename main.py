from flask import Flask, render_template_string, request, redirect, url_for, send_file
import csv
import os
from io import StringIO
from pathlib import Path
import requests
import subprocess

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"  # Ollama endpoint
MODEL = "codegemma:latest"
CSV_FILE = "test_scenarios.csv"
SCRIPT_DIR = Path("test_scripts")
SCRIPT_DIR.mkdir(exist_ok=True)
COMBINED_SCRIPT_FILE = SCRIPT_DIR / "spotify_test_suite.py"

# Function to call Ollama + CodeGemma for test scenario generation
def generate_test_scenarios(area, count):
    prompt = f"""
        You are a QA engineer automating the UI testing of the **Spotify Windows Desktop application**.

        Generate exactly **{count} unique and meaningful test scenarios** focused on the **'{area}'** functionality.

        🧠 Assume real-world usage. Be creative and comprehensive.

        📝 Format: Each line should be a single test scenario, phrased as a full sentence in imperative form.

        Example:
        - "Verify that a user can search for a song using the search bar and press Enter to navigate to the result."
        - "Ensure that clicking the Play button starts the currently selected track."

        ✅ Rules:
        - Scenarios should **simulate end-user behavior** using only keyboard-based actions.
        - Avoid duplicating ideas or actions across scenarios.
        - Make sure each test is **clear, distinct, and practically automatable**.

        Only output the test scenarios — no headings, no explanations.
    """


    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })

    if response.status_code != 200:
        scenarios = [{
            "Test Case ID": "TC_ERROR",
            "Area": area,
            "Description": f"Failed to generate test cases: {response.text}"
        }]
    else:
        text = response.json().get("response", "")
        lines = [line.strip("- ") for line in text.strip().split("\n") if line.strip()]
        scenarios = [
            {
                "Test Case ID": f"TC_{i+1}",
                "Area": area,
                "Description": line
            } for i, line in enumerate(lines[:int(count)])
        ]

    # Save to CSV file
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["Test Case ID", "Area", "Description"])
        writer.writeheader()
        writer.writerows(scenarios)

    return scenarios

# New: Function to manually generate test scripts using LLM prompt
def generate_combined_script(scenarios):
    # Create content string from CSV rows
    content = ""
    for scenario in scenarios:
        content += f"{scenario['Test Case ID']},{scenario['Area']},{scenario['Description']}\n"

    # Use expert prompt
    prompt = f"""You are an expert Python developer skilled in Windows desktop automation and UI testing.

Your task: Write a **pytest-based test script** in Python to automate a user action on the Windows Spotify desktop app.

Scenario:
The user wants to search for the song "Imagine Dragons" using keyboard and mouse automation. The known screen coordinates for the search box are (691,1)–(1304,72), and the mouse click should happen at point (700, 40).

Use the following strict coding instructions:

1. Use these imports (and others only if necessary):
     from pywinauto.application import Application
     from pywinauto.keyboard import send_keys
     import pyautogui, pytest, time

2. Define a constant path:
     SPOTIFY_PATH = r"C:\\Users\\palla\\AppData\\Local\\Microsoft\\WindowsApps\\Spotify.exe"

3. Provide this helper function (do not rename):
     def connect_spotify():
         try:
             app = Application(backend="uia").connect(title_re="Spotify.*", timeout=10)
             win = app.window(title_re="Spotify.*")
             print(f"[UIA] Window exists: {{win.exists()}} | visible: {{win.is_visible()}}")
             return app
         except Exception as e:
             print(f"[UIA] connect failed: {{e}}")
             try:
                 app = Application(backend="win32").connect(title_re="Spotify.*", timeout=10)
                 win = app.window(title_re="Spotify.*")
                 print(f"[Win32] Window exists: {{win.exists()}} | visible: {{win.is_visible()}}")
                 return app
             except Exception as e2:
                 print(f"[Win32] connect failed: {{e2}}")
                 return Application(backend="uia").start(SPOTIFY_PATH)

4. Define a pytest fixture named `spotify_app`:
     - It connects to the Spotify app
     - Yields the visible window with "Spotify" in its title
     - Sleeps for 5 seconds before starting

5. Create a pytest function `test_search_song(spotify_app)` that:
     - Uses the `spotify_app` fixture
     - Brings the Spotify window to focus
     - Moves the mouse to coordinate (700, 40) and clicks
     - Types the text "Imagine Dragons" and presses Enter using `send_keys`
     - Asserts success with a placeholder (e.g. `assert True`)
     - Includes comments for each step

Output valid Python code only. Do not include markdown or explanations.
"""

    response = requests.post(OLLAMA_URL, json={
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    })

    if response.status_code != 200:
        script_content = f"""# Failed to generate test scripts:\n# {response.text}"""
    else:
        script_content = response.json().get("response", "")

    with open(COMBINED_SCRIPT_FILE, 'w') as f:
        f.write(script_content)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        area = request.form['area']
        count = request.form['count']
        generate_test_scenarios(area, count)
        return redirect(url_for('generate_scripts'))

    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>LLM Test Scenario Generator</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background-color: #f7f9fc; }
                h2 { color: #2c3e50; }
                form {
                    background-color: #fff;
                    padding: 25px;
                    border-radius: 10px;
                    max-width: 500px;
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }
                input[type="text"], input[type="number"] {
                    width: 95%;
                    padding: 10px;
                    margin: 12px 0;
                    border-radius: 5px;
                    border: 1px solid #ccc;
                }
                input[type="submit"] {
                    background-color: #4CAF50;
                    color: white;
                    padding: 12px 20px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
                input[type="submit"]:hover {
                    background-color: #45a049;
                }
            </style>
        </head>
        <body>
            <h2>🎯 LLM Test Scenario Generator</h2>
            <form method="post">
                <label>🧪 Area for Testing:</label><br>
                <input type="text" name="area" required><br>
                <label>📋 Number of Test Cases:</label><br>
                <input type="number" name="count" required><br>
                <input type="submit" value="🚀 Generate Test Scenarios">
            </form>
        </body>
        </html>
    ''')


@app.route('/generate-scripts')
def generate_scripts():
    if not os.path.exists(CSV_FILE):
        return "No test scenarios found."

    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        scenarios = list(reader)

    generate_combined_script(scenarios)
    return redirect(url_for('edit_combined_script'))

@app.route('/edit-combined-script', methods=['GET', 'POST'])
def edit_combined_script():
    if request.method == 'POST':
        with open(COMBINED_SCRIPT_FILE, 'w') as f:
            f.write(request.form['content'])
        return redirect(url_for('edit_combined_script'))

    content = open(COMBINED_SCRIPT_FILE).read() if COMBINED_SCRIPT_FILE.exists() else ""
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edit Test Suite</title>
            <style>
                body { font-family: Arial; margin: 40px; background-color: #f2f2f2; }
                textarea { width: 100%; height: 500px; padding: 10px; font-family: monospace; font-size: 14px; }
                input[type="submit"], .push-button {
                    padding: 10px 20px;
                    margin-top: 10px;
                    font-size: 16px;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
                input[type="submit"] { background-color: #4CAF50; color: white; }
                .push-button { background-color: #007bff; color: white; text-decoration: none; display: inline-block; }
                .push-button:hover { background-color: #0056b3; }
            </style>
        </head>
        <body>
            <h2>🛠️ Editing Combined Spotify Test Suite</h2>
            <form method="post">
                <textarea name="content">{{content}}</textarea><br>
                <input type="submit" value="💾 Save">
            </form>
            <br>
            <a href="{{ url_for('push_to_git') }}" class="push-button">🚀 Push to Git</a>
        </body>
        </html>
    ''', content=content)

@app.route('/push-to-git')
def push_to_git():
    repo_path = SCRIPT_DIR.resolve()
    branch     = "main"                          # or "main"
    remote     = "origin"
    remote_url = "https://github.com/pallavi-a/WinScript.git"  # CHANGE

    try:
        # init repo if missing
        if not (repo_path / ".git").exists():
            subprocess.run(["git", "init"], cwd=repo_path, check=True)

        # set or correct the remote URL (over-writes bad ones)
        subprocess.run(["git", "remote", "remove", remote], cwd=repo_path, check=False)
        subprocess.run(["git", "remote", "add", remote, remote_url], cwd=repo_path, check=True)

        # checkout or create the branch
        subprocess.run(["git", "checkout", "-B", branch], cwd=repo_path, check=True)

        # commit latest changes
        subprocess.run(["git", "add", COMBINED_SCRIPT_FILE.name], cwd=repo_path, check=True)
        subprocess.run(["git", "commit", "-m", "Update Spotify test suite"], cwd=repo_path, check=True)

        # first push uses -u to create origin/<branch> if it doesn’t exist
        subprocess.run(["git", "pull", "--rebase", remote, branch], cwd=repo_path, check=True)
        subprocess.run(["git", "push", "-u", remote, branch], cwd=repo_path, check=True)

        return (f"<h3>✅ Pushed to <code>{remote_url}</code> "
                f"on branch <code>{branch}</code>.</h3>"
                "<a href='/edit-combined-script'>← Back</a>")

    except subprocess.CalledProcessError as e:
        return (f"<h3>❌ Git error:</h3><pre>{e}</pre>"
                "<a href='/edit-combined-script'>← Back</a>")



if __name__ == '__main__':
    app.run(debug=True)
