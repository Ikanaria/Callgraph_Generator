# callgraph.py (statical Callgraph-Analyzer with Line Counter)
# Thanks Jo for your idea and the basic structure of the script.
"""
pip install pyvis tqdm pyppeteer

Application for analyzing and visualizing the structure of a Python program
 - Searches a project folder (your_project/)
 - Extracts: Modules, Classes, async def / def, Function calls
 - Saves everything as JSON
 - Generates an interactive HTML graph visualization via PyVis
 
 Generates an interactive diagram where:
- each node is a function
- async functions are highlighted
- arrows show which function calls which
- modules are recognizable in the labels
- you can freely zoom, filter, and move

Python Callgraph Generator with:
- Clustering by modules
- Async/Sync color coding
- FastAPI routes separately
- Hover info
- Filter buttons: All / Async / Sync / Routes
- Physics toggle: Layout on/off, nodes movable
- Legend including modules
- Line counter in legend
"""

import ast, os, hashlib, argparse, sys
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Optional, Dict
from pyvis.network import Network
from collections import defaultdict, Counter

# -------------------------------
# Helpers
# -------------------------------
def generate_color_config(project_root: str) -> Dict[str, str]:
    """Generate color configuration automatically based on project root"""
    seed = hashlib.md5(project_root.encode()).hexdigest()
    return {
        "async_border": f"#{seed[:6]}",          # Border Async functions
        "sync_border": f"#{seed[6:12]}",         # Border Sync functions
        "route_background": f"#{seed[12:18]}",   # Background FastAPI-Routes
        "route_border": f"#{seed[18:24]}",       # Border FastAPI-Routes
    }

def slug_color(s: str, seed: str = "") -> str:
    h = hashlib.md5((s + seed).encode()).hexdigest()
    return f"#{h[:6]}"

def shortpath(p: str, root: str) -> str:
    try:
        return str(Path(p).resolve().relative_to(Path(root).resolve()))
    except:
        return p

# -------------------------------
# CONFIG
# -------------------------------
def resolve_config(args=None):
    """
    Resolve PROJECT_ROOT and OUTPUT_HTML dynamically.

    Priority:
      1. CLI argument --root (or positional path)
      2. Current working directory (cwd)

    Output file is placed in PROJECT_ROOT with a name derived
    from the project folder name, e.g.:
      my_project_Callgraph_20250101_120000.html
    """
    parser = argparse.ArgumentParser(
        description="Python Callgraph Generator — run against any project folder."
    )
    parser.add_argument(
        "root",
        nargs="?",
        default=None,
        help="Path to the project root (default: current working directory)",
    )
    parser.add_argument(
        "--root",
        dest="root_flag",
        default=None,
        metavar="PATH",
        help="Alternative: --root <path>",
    )
    parser.add_argument(
        "--output-dir",
        dest="output_dir",
        default=None,
        metavar="DIR",
        help="Directory to write the HTML output (default: PROJECT_ROOT)",
    )
    parser.add_argument(
        "--no-route-nodes",
        dest="route_nodes",
        action="store_false",
        default=True,
        help="Disable FastAPI route node highlighting",
    )
    parser.add_argument(
        "--no-folder-filters",
        dest="folder_filters",
        action="store_false",
        default=True,
        help="Disable folder filter buttons",
    )

    parsed = parser.parse_args(args)

    # Determine root: positional arg > --root flag > cwd
    raw_root = parsed.root or parsed.root_flag or os.getcwd()
    project_root = str(Path(raw_root).resolve())

    # Output directory
    out_dir = Path(parsed.output_dir).resolve() if parsed.output_dir else Path(project_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    project_name = Path(project_root).name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_name = f"{project_name}_Callgraph_{timestamp}.html"
    output_html = str(out_dir / output_name)

    return project_root, output_html, parsed.route_nodes, parsed.folder_filters


# Resolved at startup — safe to use as module-level constants
PROJECT_ROOT, OUTPUT_HTML, ENABLE_ROUTE_NODES, ENABLE_FOLDER_FILTERS = resolve_config()

# Color configuration automatically generated
COLOR_CONFIG = generate_color_config(PROJECT_ROOT)

# -------------------------------
# Line Counter
# -------------------------------
def count_lines_in_file(filepath: str) -> Optional[Dict[str, int]]:
    """
    Count different types of lines in a Python file
    
    Returns:
        dict with keys: total, code, comments, blank, docstrings
        or None if file cannot be read
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"X  Could not read {filepath}: {e}")
        return None
    
    total = len(lines)
    blank = 0
    comments = 0
    docstrings = 0
    code = 0
    
    in_docstring = False
    docstring_char = None
    
    for line in lines:
        stripped = line.strip()
        
        # Blank line
        if not stripped:
            blank += 1
            continue
        
        # Check for docstring start/end
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if not in_docstring:
                in_docstring = True
                docstring_char = stripped[:3]
                docstrings += 1
                # Check if docstring ends on same line
                if stripped.count(docstring_char) >= 2:
                    in_docstring = False
            else:
                in_docstring = False
                docstrings += 1
            continue
        
        # Inside docstring
        if in_docstring:
            docstrings += 1
            continue
        
        # Comment line
        if stripped.startswith('#'):
            comments += 1
            continue
        
        # Code line
        code += 1
    
    return {
        'total': total,
        'code': code,
        'comments': comments,
        'blank': blank,
        'docstrings': docstrings
    }

def analyze_project_lines(root: str, exclude_dirs: List[str] = None) -> Dict:
    """
    Analyze all Python files and count lines
    
    Returns:
        dict with overall statistics and per-directory breakdown
    """
    if exclude_dirs is None:
        exclude_dirs = ['.venv', 'venv', '__pycache__', '.git', 'node_modules']
    
    overall = {
        'total': 0, 'code': 0, 'comments': 0, 
        'blank': 0, 'docstrings': 0, 'file_count': 0
    }
    
    by_dir = defaultdict(lambda: {
        'total': 0, 'code': 0, 'comments': 0, 
        'blank': 0, 'docstrings': 0, 'files': 0
    })
    
    root_path = Path(root).resolve()
    
    for py_file in root_path.rglob('*.py'):
        # Skip excluded directories
        if any(excl in py_file.parts for excl in exclude_dirs):
            continue
        
        # Count lines
        counts = count_lines_in_file(str(py_file))
        if counts is None:
            continue
        
        # Get directory name
        try:
            rel_path = py_file.relative_to(root_path)
            dir_name = str(rel_path.parent).replace('\\', '/') if rel_path.parent != Path('.') else 'root'
        except:
            dir_name = 'unknown'
        
        # Update directory stats
        for key in ['total', 'code', 'comments', 'blank', 'docstrings']:
            by_dir[dir_name][key] += counts[key]
        by_dir[dir_name]['files'] += 1
        
        # Update overall stats
        for key in ['total', 'code', 'comments', 'blank', 'docstrings']:
            overall[key] += counts[key]
        overall['file_count'] += 1
    
    return {
        'overall': overall,
        'by_dir': dict(by_dir)
    }

# -------------------------------
# Helpers
# -------------------------------
def top_level_folder(path: str) -> str:
    if path in ("", ".", "root"):
        return "root"
    parts = path.split('/')
    if len(parts) >= 2:
        return '/'.join(parts[:2])
    return parts[0]

class FuncInfo:
    def __init__(self, module: str, name: str, filepath: str, lineno: int, is_async: bool):
        self.module = module
        self.name = name
        self.filepath = filepath
        self.lineno = lineno
        self.is_async = is_async
        self.calls: Counter[Tuple[str, Optional[str]], int] = Counter()
        self.is_route = False
        self.methods: List[str] = []
        self.paths: List[str] = []

    @property
    def id(self):
        return f"{self.module}:{self.name}:{self.lineno}"

    def tooltip(self):
        return (
            f"<b>{self.name}()</b><br>"
            f"Module: {self.module}<br>"
            f"File: {shortpath(self.filepath, PROJECT_ROOT)}:{self.lineno}<br>"
            f"Type: {'async' if self.is_async else 'sync'}<br>"
            f"Routes: {' '.join(self.methods)} {' '.join(self.paths)}"
        )

# -------------------------------
# AST Visitor
# -------------------------------
class ImportAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.alias_to_module: Dict[str, str] = {}

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name
            asname = alias.asname or name.split('.')[0]
            self.alias_to_module[asname] = name

    def visit_ImportFrom(self, node: ast.ImportFrom):
        module = node.module or ""
        for alias in node.names:
            asname = alias.asname or alias.name
            if module:
                self.alias_to_module[asname] = f"{module}.{alias.name}"
            else:
                self.alias_to_module[asname] = alias.name


class CallVisitor(ast.NodeVisitor):
    def __init__(self, imports: ImportAnalyzer):
        self.calls: Counter[Tuple[str, Optional[str]], int] = Counter()
        self.imports = imports

    def visit_Call(self, node):
        call_name = None
        root_hint = None
        if isinstance(node.func, ast.Name):
            call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            attrs = []
            cur = node.func
            while isinstance(cur, ast.Attribute):
                attrs.append(cur.attr)
                cur = cur.value
            if isinstance(cur, ast.Name):
                attrs.append(cur.id)
            attrs = list(reversed(attrs))
            if attrs:
                root_hint = ".".join(attrs[:-1]) if len(attrs) > 1 else attrs[0]
                call_name = attrs[-1]
        if call_name:
            self.calls[(call_name, self._normalize_hint(root_hint))] += 1
        self.generic_visit(node)

    def _normalize_hint(self, hint: Optional[str]) -> Optional[str]:
        if not hint:
            return None
        return self.imports.alias_to_module.get(hint, hint)

# -------------------------------
# Extract functions from file
# -------------------------------
def extract_file(filepath: str) -> List[FuncInfo]:
    with open(filepath, "r", encoding="utf-8") as f:
        src = f.read()
    try:
        tree = ast.parse(src)
    except Exception as e:
        print("PARSE ERROR:", filepath, e)
        return []

    module = Path(filepath).with_suffix("").as_posix().replace("/", ".").replace("\\", ".")

    results: List[FuncInfo] = []

    import_analyzer = ImportAnalyzer()
    import_analyzer.visit(tree)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            fi = FuncInfo(
                module=module,
                name=node.name,
                filepath=str(Path(filepath).resolve()),
                lineno=node.lineno,
                is_async=isinstance(node, ast.AsyncFunctionDef)
            )

            cv = CallVisitor(import_analyzer)
            cv.visit(node)
            fi.calls = cv.calls

            # FastAPI routes
            if ENABLE_ROUTE_NODES:
                for dec in getattr(node, "decorator_list", []):
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        attr_name = dec.func.attr.lower()
                        if attr_name in ("get","post","put","patch","delete","head","options"):
                            fi.is_route = True
                            fi.methods.append(attr_name.upper())
                            path_val = None
                            if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                                path_val = dec.args[0].value
                            for kw in dec.keywords:
                                if kw.arg in ("path","route") and isinstance(kw.value, ast.Constant):
                                    path_val = kw.value.value
                            if path_val:
                                fi.paths.append(path_val)

            results.append(fi)
    return results

# -------------------------------
# Crawl project
# -------------------------------
def crawl_project(root: str) -> List[FuncInfo]:
    results: List[FuncInfo] = []
    for d, _, files in os.walk(root):
        if any(skip in d for skip in [".venv","venv","__pycache__", ".git", "Callgraph"]):
            continue
        for f in files:
            if f.endswith(".py"):
                results.extend(extract_file(os.path.join(d, f)))
    return results

# -------------------------------
# Generate Line Stats HTML 
# -------------------------------
def generate_line_stats_html(line_stats: Dict) -> str:
    """Generate HTML for line statistics to display in legend"""
    
    overall = line_stats['overall']
    by_dir = line_stats['by_dir']
    
    # Calculate percentages
    total = overall['total']
    if total == 0:
        return "<b> Code Statistics:</b><br><i>No data</i>"
    
    code_pct = overall['code'] / total * 100
    comment_pct = overall['comments'] / total * 100
    doc_pct = overall['docstrings'] / total * 100
    blank_pct = overall['blank'] / total * 100
    
    # Overall stats HTML
    html = f"""
<b> Code Statistics:</b><br>
<div style="font-size:12px;margin-top:4px;">
<b>Overall:</b><br>
<div style="margin-left:8px;">
Files: {overall['file_count']}<br>
Total Lines: {overall['total']:,}<br>
Code: {overall['code']:,} ({code_pct:.1f}%)<br>
Comments: {overall['comments']:,} ({comment_pct:.1f}%)<br>
Docstrings: {overall['docstrings']:,} ({doc_pct:.1f}%)<br>
Blank: {overall['blank']:,} ({blank_pct:.1f}%)<br>
</div>
"""
    
    # Documentation quality indicator
    doc_ratio = (overall['comments'] + overall['docstrings']) / overall['code'] if overall['code'] > 0 else 0
    if doc_ratio < 0.1:
        quality = " Low documentation (<10%)"
    elif doc_ratio < 0.2:
        quality = " Moderate documentation (10-20%)"
    else:
        quality = " Good documentation (>20%)"
    
    html += f"<div style='margin-left:8px;color:#666;'>Doc Ratio: {doc_ratio:.2f} - {quality}</div>"
    
    # Top directories by code lines
    html += "<br><b>By Directory:</b><br>"
    sorted_dirs = sorted(by_dir.items(), key=lambda x: x[1]['code'], reverse=True)[:5]
    
    for dir_name, stats in sorted_dirs:
        html += f"""
<div style="margin-left:8px;font-size:11px;">
<b>{dir_name}</b>: {stats['code']:,} lines ({stats['files']} files)<br>
</div>
"""
    
    html += "</div>"
    
    return html

# -------------------------------
# Build PyVis graph
# -------------------------------
def build_graph(funcs: List[FuncInfo], line_stats: Dict):
    net = Network(height="1200px", width="100%", directed=True)
    net.barnes_hut()
    net.notebook = False

    # -------------------------------
    # Folder colors generate automatically based on project root and folder name
    # -------------------------------
    seed = hashlib.md5(PROJECT_ROOT.encode()).hexdigest()[:8]
    folder_colors = {}
    for f in funcs:
        rel_path = Path(f.filepath).resolve().relative_to(Path(PROJECT_ROOT).resolve())
        folder_path = str(rel_path.parent).replace('\\', '/')
        top_folder = top_level_folder(folder_path)
        if top_folder not in folder_colors:
            folder_colors[top_folder] = slug_color(top_folder, seed)

    # -------------------------------
    # Nodes
    # -------------------------------
    by_name = {}
    for f in funcs:
        rel_file = Path(f.filepath).resolve().relative_to(Path(PROJECT_ROOT).resolve())
        folder_path = str(rel_file.parent).replace('\\', '/')
        if folder_path in ("", "."):
            folder_path = "root"
        top_folder = top_level_folder(folder_path)
        file_label = f"{f.name}()"
        if f.is_async:
            file_label += " (async)"

        node_color = folder_colors[top_folder]

        net.add_node(
            f.id,
            label=file_label,
            title=f.tooltip(),
            shape="box",
            group=top_folder,
            color={
                "background": node_color,
                "border": COLOR_CONFIG["async_border"] if f.is_async else COLOR_CONFIG["sync_border"]
            }
        )
        by_name.setdefault(f.name, []).append(f)

    # -------------------------------
    # FastAPI Route Nodes
    # -------------------------------
    if ENABLE_ROUTE_NODES:
        route_nodes = {}
        for f in funcs:
            if f.is_route:
                for m, p in zip(f.methods, f.paths or [""]):
                    key = f"{m} {p}"
                    if key not in route_nodes:
                        rn = f"route:{key}"
                        net.add_node(
                            rn,
                            label=key,
                            shape="ellipse",
                            group="route",
                            color={
                                "background": COLOR_CONFIG["route_background"],
                                "border": COLOR_CONFIG["route_border"]
                            },
                            title=f"Route {key}"
                        )
                        route_nodes[key] = rn
                    net.add_edge(route_nodes[key], f.id)

    # -------------------------------
    # Helper for resolving call targets
    # -------------------------------
    def resolve_targets(name: str, hint: Optional[str], current: FuncInfo) -> List[FuncInfo]:
        candidates = by_name.get(name, [])
        if not candidates:
            return []
        if hint:
            matched = [t for t in candidates if t.module == hint or hint.endswith(t.module) or t.module.endswith(hint)]
            if matched:
                return matched
        same_module = [t for t in candidates if t.module == current.module]
        if same_module:
            return same_module
        return candidates

    # -------------------------------
    # Call edges
    # -------------------------------
    edge_counts = defaultdict(int)
    for f in funcs:
        for (name, hint), count in f.calls.items():
            targets = resolve_targets(name, hint, f)
            for t in targets:
                if t.id != f.id:
                    edge_counts[(f.id, t.id)] += count

    for (from_id, to_id), count in edge_counts.items():
        width = min(count, 10)  # Max width 10 for visibility
        title = f"{count} call{'s' if count > 1 else ''}"
        net.add_edge(from_id, to_id, width=width, title=title)

    # Write call counts to log file
    log_file = OUTPUT_HTML.replace('.html', '_calls.log')
    with open(log_file, 'w', encoding='utf-8') as f:
        f.write("From\tTo\tCalls\n")
        for (from_id, to_id), count in sorted(edge_counts.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{from_id}\t{to_id}\t{count}\n")
    print(f">> Call counts logged to: {log_file}")

    # -------------------------------
    # Options
    # -------------------------------
    net.set_options("""
{
  "nodes": {"font": {"size":14}, "physics": true},
  "edges": {"arrows":{"to":{"enabled":true}},"smooth":{"enabled":true,"type":"dynamic"}},
  "physics": {"enabled":true, "stabilization":{"enabled":true,"iterations":200}},
  "interaction": {"multiselect": true, "hover": true, "dragNodes": true}
}
""")

    # Folder filter buttons
    folder_buttons_html = ""
    if ENABLE_FOLDER_FILTERS:
        folder_buttons_html = "<br><b>Ordnerfilter:</b><br>"
        for folder in sorted(folder_colors):
            safe_folder = folder.replace("'", "\\'")
            folder_buttons_html += (
                f'<button class="folder-button active" onclick="toggleFolder(\'{safe_folder}\', this)">{folder}</button>'
            )

    # -------------------------------
    # Enhanced Legend with Line Stats
    # -------------------------------
    # Aggregate line stats by top-level folder to match the graph colors
    top_level_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {
        'total': 0, 'code': 0, 'comments': 0,
        'blank': 0, 'docstrings': 0, 'files': 0
    })
    for folder_name, stats in line_stats['by_dir'].items():
        top_folder = top_level_folder(folder_name)
        for key, value in stats.items():
            top_level_stats[top_folder][key] += value

    module_legend_html = "<b>Ordnerstruktur:</b><br>"
    for folder, color in folder_colors.items():
        folder_stats = top_level_stats.get(folder, {})
        code_lines = folder_stats.get('code', 0)
        file_count = folder_stats.get('files', 0)
        
        module_legend_html += (
            f'<div style="display:flex;align-items:center;margin-bottom:2px;">'
            f'<div style="width:18px;height:18px;background:{color};border:2px solid #444;border-radius:4px;margin-right:8px;"></div>'
            f'<div style="font-size:13px;color:#111;">{folder}</div>'
            f'<div style="font-size:10px;color:#666;margin-left:8px;">({code_lines:,} lines, {file_count} files)</div>'
            f'</div>'
        )
    
    # Generate line statistics HTML
    line_stats_html = generate_line_stats_html(line_stats)
    route_button_html = '<button id="filter-routes" class="filter-button" onclick="filterRoutes()">Routes</button>' if ENABLE_ROUTE_NODES else ''
    route_legend_html = '<div style="display:flex;align-items:center;margin-bottom:2px;"><div style="width:18px;height:18px;background:' + COLOR_CONFIG['route_background'] + ';border:2px solid ' + COLOR_CONFIG['route_border'] + ';border-radius:10px;margin-right:8px;"></div><div style="font-size:13px;color:#111;">FastAPI Route</div></div>' if ENABLE_ROUTE_NODES else ''

    js_inject = """
<script>
function updateNodeVisibility(predicate) {
  const nodes = network.body.data.nodes.get();
  const updated = nodes.map(n => ({ ...n, hidden: !predicate(n) }));
  network.body.data.nodes.update(updated);
}
function clearActiveFilter() {
  document.querySelectorAll('.filter-button').forEach(btn => btn.classList.remove('active'));
}
function setActiveFilter(id, label) {
  clearActiveFilter();
  const btn = document.getElementById(id);
  if (btn) btn.classList.add('active');
  const labelEl = document.getElementById('active-filter-label');
  if (labelEl) labelEl.textContent = 'Aktiver Filter: ' + label;
}
function resetFolderButtons() {
  document.querySelectorAll('.folder-button').forEach(btn => btn.classList.add('active'));
}
function filterAll() {
  updateNodeVisibility(() => true);
  setActiveFilter('filter-all', 'All');
  resetFolderButtons();
}
function filterAsync() {
  updateNodeVisibility(n => n.label && n.label.includes('(async)'));
  setActiveFilter('filter-async', 'Async');
}
function filterSync() {
  updateNodeVisibility(n => !n.label || !n.label.includes('(async)'));
  setActiveFilter('filter-sync', 'Sync');
}
function filterRoutes() {
  updateNodeVisibility(n => n.group === 'route');
  setActiveFilter('filter-routes', 'Routes');
}
function toggleFolder(folder, button) {
  const nodes = network.body.data.nodes.get();
  const updated = nodes.map(n => n.group === folder ? ({ ...n, hidden: !n.hidden }) : n);
  network.body.data.nodes.update(updated);
  if (button) button.classList.toggle('active');
}
function clearActivePhysics() {
  document.querySelectorAll('.physics-button').forEach(btn => btn.classList.remove('active'));
}
function setPhysics(enabled) {
  network.setOptions({physics:{enabled:enabled}});
  clearActivePhysics();
  const id = enabled ? 'physics-on' : 'physics-off';
  const btn = document.getElementById(id);
  if (btn) btn.classList.add('active');
}
</script>
<style>
.filter-button, .folder-button, .physics-button {
  margin: 2px 3px 2px 0;
  padding: 6px 12px;
  min-width: 60px;
  border-radius: 6px;
  border: 1px solid #888;
  background: #f2f4f7;
  color: #111;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s ease;
}
.filter-button.active, .folder-button.active, .physics-button.active {
  background: #005a9e;
  color: #fff;
  border-color: #003f70;
  box-shadow: 0 0 0 2px rgba(0, 122, 204, 0.22);
}
.filter-button:hover, .folder-button:hover, .physics-button:hover {
  background: #e8f3ff;
}
</style>
<div style="position:fixed;top:10px;left:10px;z-index:999;background:#fff;padding:8px;border:1px solid #aaa;max-width:320px;overflow:auto;max-height:90vh;font-family:Arial, sans-serif;">
<b>Filter:</b><br>
<button id="filter-all" class="filter-button active" onclick="filterAll()">All</button>
<button id="filter-async" class="filter-button" onclick="filterAsync()">Async</button>
<button id="filter-sync" class="filter-button" onclick="filterSync()">Sync</button>
{route_button_html}
<div id="active-filter-label" style="margin-top:6px;font-size:12px;font-weight:700;color:#333;">Aktiver Filter: All</div>
<br><br>
{folder_buttons_html}
<br><br>
<b>Physics:</b><br>
<button id="physics-on" class="physics-button filter-button active" onclick="setPhysics(true)">On</button>
<button id="physics-off" class="physics-button filter-button" onclick="setPhysics(false)">Off</button>
<br><br>
{line_stats_html}
<br>
<div style="margin-top:4px;">
{route_legend_html}
<br>
{module_legend_html}
</div>
</div>
"""
    js_inject = js_inject.replace('{folder_buttons_html}', folder_buttons_html)
    js_inject = js_inject.replace('{line_stats_html}', line_stats_html)
    js_inject = js_inject.replace('{route_button_html}', route_button_html)
    js_inject = js_inject.replace('{route_legend_html}', route_legend_html)
    js_inject = js_inject.replace('{module_legend_html}', module_legend_html)
    js_inject = js_inject.replace('{async_border}', COLOR_CONFIG['async_border'])
    js_inject = js_inject.replace('{sync_border}', COLOR_CONFIG['sync_border'])
    html = net.generate_html(notebook=False)
    html = html.replace("</body>", js_inject + "\n</body>")

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    print(f">> HTML gespeichert: {OUTPUT_HTML}")

# -------------------------------
# Main
# -------------------------------
def main():
    print("\n" + "="*70)
    print(">> Python Callgraph Generator")
    print("="*70)
    print(f">> Projektordner : {PROJECT_ROOT}")
    print(f">> Output        : {OUTPUT_HTML}\n")
    
    # Count lines first
    print(">> Counting lines of code...")
    line_stats = analyze_project_lines(PROJECT_ROOT)
    overall = line_stats['overall']
    print(f"   >> Analyzed {overall['file_count']} files")
    print(f"   >> Total lines: {overall['total']:,}")
    print(f"   >> Code lines: {overall['code']:,} ({overall['code']/overall['total']*100:.1f}%)\n")
    
    # Extract functions
    print("> Extracting functions...")
    funcs = crawl_project(PROJECT_ROOT)
    print(f"   >> {len(funcs)} Funktionen gefunden.\n")
    
    # Build graph with line stats
    print("> Building interactive graph...")
    build_graph(funcs, line_stats)
    
    print("\n" + "="*70)
    print(">>> Fertig!")
    print(f"--> Open: {OUTPUT_HTML}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()