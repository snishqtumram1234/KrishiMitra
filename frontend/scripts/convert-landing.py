"""Convert the unpacked Claude Design landing template into Next.js files, mechanically (nothing retyped by hand).

Reads /tmp/lp/template.html. Writes (under the frontend):
  public/landing/fonts/<uuid>.woff2
  src/components/landing/landing.css
  src/components/landing/HeroArt.tsx
  src/components/landing/body.generated.tsx   (the page markup, with the {{bindings}} turned into React expressions)
"""
import re, shutil, json
from pathlib import Path

FRONT = Path(r"C:\Users\tumra\Documents\KrishiMitra\frontend")
SRC = Path("/tmp/lp") if Path("/tmp/lp").exists() else Path(r"C:\Users\tumra\AppData\Local\Temp\lp")
t = (SRC / "template.html").read_text(encoding="utf-8")

# ------------------------------------------------------------------ fonts
fonts_dir = FRONT / "public" / "landing" / "fonts"
fonts_dir.mkdir(parents=True, exist_ok=True)
blocks = re.findall(r"(?:/\*[^*]*\*/\s*)?(@font-face\s*\{[^}]*\})", t)
local = [b for b in blocks if re.search(r'url\("?[0-9a-f\-]{36}"?\)', b)]
face_css = []
for b in local:
    uid = re.search(r'url\("?([0-9a-f\-]{36})"?\)', b).group(1)
    shutil.copy(SRC / f"{uid}.woff2", fonts_dir / f"{uid}.woff2")
    face_css.append(re.sub(r'url\("?[0-9a-f\-]{36}"?\)', f'url("/landing/fonts/{uid}.woff2")', re.sub(r"\s+", " ", b)))

# ------------------------------------------------------------------ css
style_blocks = re.findall(r"<style>(.*?)</style>", t, flags=re.S)
page_css = [s for s in style_blocks if ".km-wrap" in s][0]
# scope the three global rules to the landing page so they cannot leak into the rest of the app
page_css = page_css.replace("body{margin:0;background:#2F4A36}", "")
page_css = page_css.replace("html{scroll-behavior:smooth}", "html:has(.km){scroll-behavior:smooth}")
page_css = page_css.replace("a{color:#E2CF9F}a:hover{color:#F0E3C0}", ":where(.km) a{color:#E2CF9F}:where(.km) a:hover{color:#F0E3C0}")
header = """/* Generated from the Claude Design landing export by scripts/convert-landing.py. Do not edit by hand.
   Scoped to .km. The few lines at the end undo app-wide base styles (line-height, heading font) so this page
   renders exactly like the original, which had no such base styles. */
"""
guard = """
/* ---- isolation from the app's base styles (the original page had none) ---- */
.km{line-height:normal;font-size:16px;font-weight:400}
.km h3:not(.km-serif){font-family:inherit}
:where(.km) a{text-decoration:revert}
.km a.km-link,.km a.km-btn{text-decoration:none}
:where(.km) svg{display:revert;vertical-align:revert}
:where(.km) button{font:revert;letter-spacing:revert;text-transform:revert;padding:revert}
"""
(FRONT / "src/components/landing").mkdir(parents=True, exist_ok=True)
(FRONT / "src/components/landing/landing.css").write_text(header + "\n".join(face_css) + "\n" + page_css.strip() + "\n" + guard, encoding="utf-8")

# ------------------------------------------------------------------ markup
body = t[t.index('<div class="km {{rootClass}}"'): t.rindex("</x-dc>")]
body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
body = body.rstrip()
assert body.endswith("</div>")

SVG_ATTR = {"sc-camel-view-box": "viewBox", "sc-camel-preserve-aspect-ratio": "preserveAspectRatio"}

def camel(name):
    if name in SVG_ATTR:
        return SVG_ATTR[name]
    if name == "class":
        return "className"
    if name.startswith(("aria-", "data-")):
        return name
    if "-" in name:
        parts = name.split("-")
        return parts[0] + "".join(p.capitalize() for p in parts[1:])
    return name

def tpl(value):
    """'a {{x}} b' -> JS template literal `a ${x} b`; a lone '{{x}}' -> the bare expression."""
    m = re.fullmatch(r"\{\{\s*([^}]+?)\s*\}\}", value)
    if m:
        return m.group(1), True
    esc = value.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    return "`" + re.sub(r"\{\{\s*([^}]+?)\s*\}\}", lambda mm: "${" + mm.group(1) + "}", esc) + "`", False

def css_prop(p):
    p = p.strip()
    if p.startswith("--"):
        return p
    p = re.sub(r"^-ms-", "ms-", p)
    parts = p.split("-")
    out = parts[0] + "".join(x.capitalize() for x in parts[1:])
    return "Webkit" + out[len("-webkit"):] if p.startswith("-webkit-") else out

def style_obj(value):
    items = []
    # split on ';' that is not inside parentheses
    depth, cur, decls = 0, "", []
    for ch in value:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == ";" and depth == 0:
            decls.append(cur)
            cur = ""
        else:
            cur += ch
    decls.append(cur)
    for d in decls:
        if not d.strip():
            continue
        k, v = d.split(":", 1)
        expr, bare = tpl(v.strip())
        items.append(f"{css_prop(k)}: {expr if '{{' in v else json.dumps(v.strip(), ensure_ascii=False)}")
    return "{{ " + ", ".join(items) + " }}"

TAG = re.compile(r"<(/?)([A-Za-z][\w:-]*)((?:\s+[^\s=>/]+(?:\s*=\s*(?:\"[^\"]*\"|'[^']*'))?)*)\s*(/?)>", re.S)
ATTR = re.compile(r"([^\s=>/]+)(?:\s*=\s*(\"[^\"]*\"|'[^']*'))?")

def attrs_jsx(raw, tag):
    out = []
    for m in ATTR.finditer(raw):
        name, val = m.group(1), m.group(2)
        val = val[1:-1] if val is not None else None
        if name in ("hint-placeholder-count", "hint-placeholder-val", "data-canvas-width", "data-canvas-height"):
            continue
        if name == "sc-camel-on-click":
            out.append(f"onClick={{{tpl(val)[0]}}}")
            continue
        if name == "style":
            out.append(f"style={style_obj(val)}")
            continue
        jname = camel(name)
        if val is None:
            out.append(jname)
        elif "{{" in val:
            expr, bare = tpl(val)
            out.append(f"{jname}={{{expr}}}")
        elif '"' in val:
            out.append(f"{jname}={{{json.dumps(val, ensure_ascii=False)}}}")
        else:
            out.append(f'{jname}="{val}"')
    return (" " + " ".join(out)) if out else ""

def convert(html):
    out, pos = [], 0
    for m in TAG.finditer(html):
        text = html[pos:m.start()]
        out.append(text_jsx(text))
        pos = m.end()
        close, tag, raw, selfc = m.group(1), m.group(2), m.group(3), m.group(4)
        if tag == "sc-for":
            if close:
                out.append("</Fragment>))}")
            else:
                lst = re.search(r'list="\{\{\s*(\w+)\s*\}\}"', raw).group(1)
                var = re.search(r'as="(\w+)"', raw).group(1)
                out.append("{" + lst + ".map((" + var + ", __i) => (<Fragment key={__i}>")
            continue
        if tag == "sc-if":
            if close:
                out.append("</>)}")
            else:
                cond = re.search(r'value="\{\{\s*(\w+)\s*\}\}"', raw).group(1)
                out.append("{" + cond + " && (<>")
            continue
        if close:
            out.append(f"</{tag}>")
        elif tag == "br" or selfc:
            out.append(f"<{tag}{attrs_jsx(raw, tag)} />")
        else:
            out.append(f"<{tag}{attrs_jsx(raw, tag)}>")
    out.append(text_jsx(html[pos:]))
    return "".join(out)

def text_jsx(s):
    s = re.sub(r"\{\{\s*([^}]+?)\s*\}\}", lambda m: "\u0001" + m.group(1) + "\u0002", s)
    assert "{" not in s and "}" not in s, s[:80]
    return s.replace("\u0001", "{").replace("\u0002", "}")

# ---- split out the hero art (a large generated <svg>) into its own component
m = re.search(r'(<div class="km-hero-art" aria-hidden="true">\s*<div style="[^"]*">\s*)(<svg .*?</svg>)', body, flags=re.S)
hero_svg = m.group(2)
body = body.replace(hero_svg, "<HeroArt />")
hero_jsx = convert(hero_svg)
(FRONT / "src/components/landing/HeroArt.tsx").write_text(
    "// Generated from the Claude Design landing export. Do not edit by hand.\n"
    "export function HeroArt() {\n  return (\n" + hero_jsx + "\n  );\n}\n", encoding="utf-8")

jsx = convert(body)

# Only the destinations of the four call-to-action links change (the original pointed them at on-page anchors that had
# no app behind them): they now open the real screens, and the proxy sends signed-out visitors to sign-in first.
for old, new in [
    ('className="km-btn" href="#start"', 'className="km-btn" href="/checks/new"'),
    ('className="km-btn is-dark" href="#start"', 'className="km-btn is-dark" href="/checks/new"'),
    ('className="km-btn is-dark" href="#ask"', 'className="km-btn is-dark" href="/checks/new?mode=question"'),
    ('href="#experts" className="km-hover-zoom"', 'href="/expert" className="km-hover-zoom"'),
]:
    assert jsx.count(old) == 1, old
    jsx = jsx.replace(old, new)

# ---- the original script's data, copied verbatim
script = re.search(r'<script type="text/x-dc" data-dc-script[^>]*>(.*?)</script>', t, flags=re.S).group(1)
def grab(start_pat):
    i = script.index(start_pat) + len(start_pat) - 1  # position of '['
    depth = 0
    for j in range(i, len(script)):
        if script[j] == "[": depth += 1
        elif script[j] == "]":
            depth -= 1
            if depth == 0:
                return script[i:j + 1]
raw_steps = grab("var raw = [")
intents = grab("intents: [")
states = grab("states: [")
HEAD = "// Copied verbatim from the Claude Design landing export. Do not edit by hand."
(FRONT / "src/components/landing/data.generated.ts").write_text(
    HEAD + chr(10)
    + "export const RAW_STEPS: { step: string; model: string; note: string; ms: string; skip?: boolean }[] = " + raw_steps + ";" + chr(10) + chr(10)
    + "export const INTENTS: { num: string; q: string; route: string; what: string; photo: string; state: string }[] = " + intents + ";" + chr(10) + chr(10)
    + "export const STATES: { num: string; title: string; code: string; text: string }[] = " + states + ";" + chr(10),
    encoding="utf-8",
)
(FRONT / "src/components/landing/body.generated.tsx").write_text(
    "// Generated from the Claude Design landing export. Do not edit by hand.\n"
    "/* eslint-disable */\n"
    'import { Fragment, type MouseEventHandler } from "react";\n'
    'import { HeroArt } from "./HeroArt";\n\n'
    "export type LandingView = {\n"
    "  rootClass: string; navClass: string; parallax: number; needle: number; showResult: boolean;\n"
    "  prev: MouseEventHandler; next: MouseEventHandler; play: MouseEventHandler;\n"
    "  intents: { num: string; q: string; route: string; what: string; photo: string; state: string }[];\n"
    "  steps: { step: string; model: string; note: string; ms: string; cls: string }[];\n"
    "  leafOpts: { label: string; bg: string; fg: string; border: string; pick: MouseEventHandler }[];\n"
    "  states: { num: string; title: string; code: string; text: string }[];\n"
    "};\n\n"
    "export function LandingBody({ rootClass, navClass, parallax, needle, showResult, prev, next, play, intents, steps, leafOpts, states }: LandingView) {\n"
    "  return (\n" + jsx + "\n  );\n}\n", encoding="utf-8")
print("css", len(face_css), "faces; hero", len(hero_jsx), "chars; body", len(jsx), "chars")
