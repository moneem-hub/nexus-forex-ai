"""
ONE-TIME: move the Agent tab's CSS out of tabs/agent_tab.py into assets/agent_tab.css.
After this, restyling = edit assets/agent_tab.css, save, refresh the browser. No Python changes, no restart.
Run from the project root:  python split_styles.py      (commit first, so you can undo with: git checkout tabs/agent_tab.py)
"""
import re
from pathlib import Path

py, css = Path("tabs/agent_tab.py"), Path("assets/agent_tab.css")
src = py.read_text(encoding="utf-8")
if "_CSS_FILE" in src:
    raise SystemExit("Already split: nothing to do.")
m = re.search(r'_CSS = """\n<style>\n(.*?)</style>\n"""\n', src, re.S)
if not m or "_md(_CSS)" not in src or "import math\n" not in src:
    raise SystemExit("tabs/agent_tab.py is not the expected version; no changes made. Replace it with the latest one first.")

css.parent.mkdir(exist_ok=True)
css.write_text(m.group(1), encoding="utf-8")
loader = '''_CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "agent_tab.css"


def _css() -> str:
    """The tab's styling lives in assets/agent_tab.css: edit that file, save, then refresh the browser."""
    return "<style>" + _CSS_FILE.read_text(encoding="utf-8") + "</style>"
'''
src = src.replace(m.group(0), loader).replace("_md(_CSS)", "_md(_css())").replace("import math\n", "import math\nfrom pathlib import Path\n", 1)
py.write_text(src, encoding="utf-8")
print(f"Done. Styling is now in {css}  ({len(m.group(1).splitlines())} lines). Edit it freely; save and refresh the browser.")
