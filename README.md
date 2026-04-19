# Callgraph Generator – README

### 0. What is a Callgraph?
A callgraph is a visual representation of how functions in your code interact with each other. It shows which functions call which others, like a flowchart of your program's logic. This helps you understand the structure of your code, find bottlenecks, or spot areas that might need refactoring.

- **Nodes (boxes):** Represent functions or modules.
- **Edges (arrows):** Show calls between functions (thicker arrows mean more calls).
- **Colors:** Group related functions (e.g., by module or async/sync type).

This tool analyzes your Python project and generates an interactive HTML graph you can explore in a browser.

### 1. Overview

This tool creates an interactive visualization of your Python application, based on function calls and module structure.
The output is an HTML file that you can open in your browser, along with a timestamped log file containing call counts.

Features:
- Functions grouped by module (clusters) and subfolders
- Async / Sync functions color-coded
- FastAPI routes highlighted separately
- Hover info: File, line, type, routes
- Interactive filter buttons: All / Async / Sync / Routes
- Physics toggle: Layout on/off, movable nodes
- Call counts: Edge width indicates call frequency
- Timestamped outputs: Each run creates unique HTML and log files

### 2. Installation

Python 3.9+ is required.
Install the packages:

```
pip install pyvis tqdm pyppeteer
```

Optional: Chromium is needed for PNG/PDF export via pyppeteer.

If you don't have Python or pip, download Python from python.org and follow the installation guide.

### 3. Usage

1. **Run the script:** Open a terminal/command prompt in the same folder as the script and type:
```
python callgraph.py
```
   The script will automatically use the current directory as the project root. To target a different project, pass the path as an argument:
```
python callgraph.py /path/to/your/project
```
   Wait for it to finish – it will show progress and create the files.

2. **Open the HTML file:** Look for a file like `projectname_Callgraph_YYYYMMDD_HHMMSS.html` in the same folder. Double-click to open in your browser.

3. **Explore in the browser:**
    - Move nodes by dragging them.
    - Toggle physics on/off to let nodes arrange automatically or manually.
    - Use filters (All / Async / Sync / Routes) to show only certain types of functions.
    - Hover over nodes for details (name, file, line).
    - Thicker arrows show functions that are called more often.

### 4. Interpreting the Graph

#### 4.1 Nodes
- Box = Function
- Async functions: Black border (runs in background, non-blocking)
- Sync functions: Dark gray border (runs sequentially, blocking)
- FastAPI routes: Orange border, oval shape (web endpoints)

Hover over nodes shows:
- Function name
- Module / File / Line
- Async / Sync
- Associated routes (if any)

#### 4.2 Edges / Arrows
- Indicate function calls: Source → Target
- Width indicates call frequency (thicker = more calls)
- Async / Sync: Black or dark gray
- FastAPI routes: Orange

#### 4.3 Clusters
- Color-coded by module and subfolder
- Functions from the same module/subfolder are grouped together
- Helps recognize the module structure at a glance

#### 4.4 Filter Buttons
- All: Show all functions
- Async: Show only asynchronous functions
- Sync: Show only synchronous functions
- Routes: Show only FastAPI routes

#### 4.5 Physics Toggle
- On: Automatic layout, nodes move
- Off: Nodes stay where you drag them

Tip: Keep physics on initially for a clean layout. Then turn it off and arrange nodes manually for presentations.

### 5. Outputs
- **HTML File:** Interactive graph (timestamped, e.g., `Callgraph_YYYYMMDD_HHMMSS.html`)
- **Log File:** Tab-separated call counts (timestamped, e.g., `Callgraph_YYYYMMDD_HHMMSS_calls.log`)
  - Columns: From, To, Calls
  - Sorted by call frequency (highest first)

### 6. Troubleshooting
- **Script doesn't run:** Ensure Python 3.13 is installed and in your PATH. Type `python --version` in the terminal to check.
- **Packages not found:** Run `pip install pyvis tqdm pyppeteer` again. If pip is not recognized, use `python -m pip install ...`.
- **HTML doesn't open:** Use a modern browser like Chrome or Firefox. If it's blocked, right-click the file and select "Open with" > your browser.
- **No graph generated:** Check the terminal output for errors. Ensure the PROJECT_ROOT path is correct and points to a folder with Python files.
- **Graph is empty:** The project might have no analyzable functions, or the path is wrong.
- **Performance issues:** For large projects (>1000 functions), use filters to reduce clutter.

### 7. Best Practices
- Large projects (>100 functions): Use filters to maintain overview
- Manually arrange moved nodes for presentations
- Modules with many functions can be quickly identified by colors and clusters
- Review the log file for call hotspots and potential refactoring opportunity
- Timestamped files allow historical comparison of code changes

### 8. Author and Credits
- **Author:** 🍀 Franziska Tannert
- **Member of Team Yotsuba**
```
   (\/)  (\/)
    \/    \/
       \/
       /\
    /\    /\
   (/\)  (/\)
```
- **AI Assistance:** This code was written with support from GitHub Copilot and Claude (Anthropic).
- **Based on:** Original code by Jo Jauch (former colleague).
