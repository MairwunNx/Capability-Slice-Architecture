"""Draws the diagrams of the specification in a light and a dark variant.

    python3 tools/diagrams.py              # every diagram
    python3 tools/diagrams.py flow rules   # only these

Each diagram lands in docs/images as <name>-light.svg and <name>-dark.svg. Markdown shows the pair through <picture>
with prefers-color-scheme. Pillow measures the text, so boxes fit their labels: install it with "pip install Pillow".

The palette below gives every entity one accent. Capsa draws its diagrams with the same palette, so an intent is blue
and a work is green in both repositories. Change a colour here and in Capsa's tools/diagrams.py together.
"""
import html
import math
import os
import pathlib
import re
import sys

from PIL import ImageFont

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "images"

# ---------- Palette ----------

# Page colours of GitHub. The background matches the page, so the picture blends in when the themes agree
# and still reads as a card when they don't.
THEMES = {
    "light": dict(bg="#ffffff", fg="#1f2328", muted="#59636e", border="#d0d7de", line="#818b98", card="#f6f8fa",
                  tint="0.08", danger="#cf222e", on_solid="#ffffff"),
    "dark": dict(bg="#0d1117", fg="#e6edf3", muted="#9198a1", border="#30363d", line="#6e7681", card="#161b22",
                 tint="0.14", danger="#f85149", on_solid="#ffffff"),
}

# One accent per family of entities, readable as text on the page of its theme.
ACCENTS = {
    "ui": dict(light="#0969da", dark="#4493f8"),          # UI, Slot, Intent
    "runtime": dict(light="#4f46e5", dark="#8b8cf8"),     # Runtime, Fact
    "capability": dict(light="#8250df", dark="#ab7df8"),  # Capability, Decision
    "slice": dict(light="#bf3989", dark="#db61a2"),       # Slice
    "projection": dict(light="#1b7c83", dark="#39c5cf"),  # Projection
    "work": dict(light="#1a7f37", dark="#3fb950"),        # Work, Signal
    "effect": dict(light="#bc4c00", dark="#f0883e"),      # Effect, Host
}
# The runtime box is filled solid. White text needs a deeper indigo than the dark accent.
RUNTIME_SOLID = dict(light="#4f46e5", dark="#5b52e0")

ENTITY = {
    "UI": "ui", "Slot": "ui", "Intent": "ui",
    "Runtime": "runtime", "Fact": "runtime",
    "Capability": "capability", "Decision": "capability",
    "Slice": "slice", "Projection": "projection",
    "Work": "work", "Signal": "work",
    "Effect": "effect", "Host": "effect",
}

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, monospace"


def font(size, bold=False):
    """Helvetica on a Mac, its metric twin on Linux."""
    for path, index in (("/System/Library/Fonts/Helvetica.ttc", 1 if bold else 0),
                        ("/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf" % ("Bold" if bold else "Regular"), 0)):
        if os.path.exists(path):
            return ImageFont.truetype(path, size, index=index)
    raise SystemExit("no Helvetica or Liberation Sans to measure the text")


SLACK = 1.08  # browsers pick other fonts: leave room
_FONTS = {}


def tw(text, size, bold=False):
    key = (size, bold)
    if key not in _FONTS:
        _FONTS[key] = font(size, bold)
    return _FONTS[key].getlength(text) * SLACK


def wrap(text, size, limit, bold=False):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if tw(trial, size, bold) <= limit or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line]


# ---------- Drawing ----------

def keep_spaces(s):
    """SVG collapses a run of spaces and drops leading ones. No-break spaces keep them, so an indent in mono text survives."""
    return re.sub(r"^ +| {2,}", lambda m: "\xa0" * len(m.group()), s)


class Drawing:
    def __init__(self, theme, w, h, title, desc):
        self.t, self.theme, self.w, self.h, self.title, self.desc = THEMES[theme], theme, w, h, title, desc
        self.parts, self.style, self.markers = [], "", {}

    def accent(self, family):
        return ACCENTS[family][self.theme]

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=13, color=None, bold=False, anchor="start", mono=False, opacity=None):
        attrs = f'x="{x:g}" y="{y:g}" font-size="{size}" fill="{color or self.t["fg"]}"'
        if bold:
            attrs += ' font-weight="700"'
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        if mono:
            attrs += f' font-family="{MONO}"'
        if opacity:
            attrs += f' fill-opacity="{opacity}"'
        self.add(f"<text {attrs}>{html.escape(keep_spaces(s), quote=False)}</text>")

    def rect(self, x, y, w, h, fill="none", stroke=None, rx=10, sw=1.5, dash=None, fill_opacity=None, stroke_opacity=None):
        attrs = f'x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx}" fill="{fill}"'
        if fill_opacity:
            attrs += f' fill-opacity="{fill_opacity}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="{sw}"'
        if stroke_opacity:
            attrs += f' stroke-opacity="{stroke_opacity}"'
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        self.add(f"<rect {attrs}/>")

    def path(self, points, color=None, dashed=False, arrow=True, sw=1.6):
        d = " ".join(("M" if i == 0 else "L") + f"{x:g} {y:g}" for i, (x, y) in enumerate(points))
        attrs = f'd="{d}" fill="none" stroke="{color or self.t["line"]}" stroke-width="{sw}" stroke-linejoin="round"'
        if dashed:
            attrs += ' stroke-dasharray="6 5"'
        if arrow:
            attrs += f' marker-end="url(#{self.marker(color or self.t["line"])})"'
        self.add(f"<path {attrs}/>")

    def marker(self, color):
        """One arrowhead per colour, defined once in <defs>."""
        if color not in self.markers:
            self.markers[color] = f"m{len(self.markers)}"
        return self.markers[color]

    def box(self, x, y, w, h, family=None, title="", sub="", solid=False, title_size=16):
        """A rounded box with a bold title and a muted line under it, both centred."""
        if solid:
            self.rect(x, y, w, h, fill=RUNTIME_SOLID[self.theme], stroke=RUNTIME_SOLID[self.theme])
            fg, muted, op = self.t["on_solid"], self.t["on_solid"], "0.85"
        elif family:
            accent = self.accent(family)
            self.rect(x, y, w, h, fill=accent, fill_opacity=self.t["tint"], stroke=accent, stroke_opacity="0.7")
            fg, muted, op = self.t["fg"], self.t["muted"], None
        else:
            self.rect(x, y, w, h, fill=self.t["card"], stroke=self.t["border"])
            fg, muted, op = self.t["fg"], self.t["muted"], None
        for s, size, bold in ((title, title_size, True), (sub, 13, False)):
            if s and tw(s, size, bold) + 20 > w:
                raise SystemExit(f"{self.title}: “{s}” does not fit a box {w} wide")
        cx = x + w / 2
        if sub:
            self.text(cx, y + h / 2 - 3, title, title_size, fg, bold=True, anchor="middle")
            self.text(cx, y + h / 2 + 17, sub, 13, muted, anchor="middle", opacity=op)
        else:
            self.text(cx, y + h / 2 + title_size * 0.35, title, title_size, fg, bold=True, anchor="middle")

    def step(self, cx, cy, n, label=None):
        """A numbered circle and the label to its right."""
        self.add(f'<circle cx="{cx:g}" cy="{cy:g}" r="11" fill="{RUNTIME_SOLID[self.theme]}"/>')
        self.text(cx, cy + 4.5, str(n), 12, self.t["on_solid"], bold=True, anchor="middle")
        if label:
            self.text(cx + 19, cy + 5, label, 14)

    def cross(self, cx, cy, r=6, color=None):
        c = color or self.t["danger"]
        self.add(f'<path d="M{cx - r:g} {cy - r:g} L{cx + r:g} {cy + r:g} M{cx + r:g} {cy - r:g} L{cx - r:g} {cy + r:g}" '
                 f'stroke="{c}" stroke-width="2" stroke-linecap="round"/>')

    def svg(self):
        defs = "".join(
            f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10z" fill="{color}"/></marker>'
            for color, mid in self.markers.items())
        head = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'font-family="{SANS}" role="img">\n'
                f"<title>{html.escape(self.title, quote=False)}</title>\n<desc>{html.escape(self.desc, quote=False)}</desc>\n")
        if self.style:
            head += f"<style>{self.style}</style>\n"
        if defs:
            head += f"<defs>{defs}</defs>\n"
        head += f'<rect width="{self.w}" height="{self.h}" rx="12" fill="{self.t["bg"]}"/>\n'
        return head + "\n".join(self.parts) + "\n</svg>\n"


# ---------- Diagrams ----------

FLOW_DESC = ("1: the UI sends an intent to the runtime, which keeps a queue of facts. 2: the runtime hands the fact to a capability, "
             "a function of the slice and the fact. 3: the capability returns a decision. 4: the runtime starts a work, a request "
             "or a subscription, and the work answers with a signal. 5: the runtime stores the new slice, the projection turns it "
             "into a UI model, and the UI shows it. 6: the runtime sends an effect to the host, which navigates or reports analytics.")

# The routes of the flow diagram, shared by the still and the animated variant.
FLOW_ROUTES = [
    ("ui", [(204, 228), (371, 228)]),                           # 1 Intent
    ("runtime", [(474, 198), (474, 78), (710, 78)]),            # 2 fact
    ("capability", [(712, 112), (517, 112), (517, 196)]),       # 3 Decision
    ("work", [(576, 214), (710, 214)]),                         # 4 start
    ("work", [(712, 244), (578, 244)]),                         # Signal
    ("slice", [(440, 258), (440, 404)]),                        # 5 new slice
    ("projection", [(373, 436), (118, 436), (118, 260)]),       # ui
    ("effect", [(517, 258), (517, 382), (710, 382)]),           # 6 Effect
]


def flow(theme, animated=False):
    d = Drawing(theme, 980, 490, "How a fact flows through a screen" + (", animated" if animated else ""), FLOW_DESC)
    d.box(34, 198, 170, 60, "ui", "UI", "slots render slices")
    d.box(373, 198, 203, 60, None, "Runtime", "queue of facts", solid=True)
    d.box(712, 48, 237, 80, "capability", "Capability", "(Slice, Fact) → Decision", title_size=17)
    d.box(712, 198, 237, 60, "work", "Work", "request or subscription")
    d.box(712, 352, 237, 60, "effect", "Host", "navigation, analytics")
    d.box(373, 406, 203, 60, "projection", "Projection", "Slice → UI model")

    dashed = {2, 4, 6}
    for i, (_, pts) in enumerate(FLOW_ROUTES):
        d.path(pts, dashed=i in dashed)

    d.step(240, 208, 1, "Intent")
    d.step(580, 60, 2, "fact")
    d.step(580, 130, 3, "Decision")
    d.step(612, 198, 4, "start")
    d.text(632, 268, "Signal", 14)
    d.step(338, 332, 5, "new slice")
    d.text(232, 456, "ui model", 14)
    d.step(580, 364, 6, "Effect")

    if animated:
        token(d)
    return d


def token(d):
    """A dot runs each route in turn, in the colour of what travels there. CSS keyframes work inside <img> too."""
    speed, pause, fade = 170.0, 0.35, 0.12
    frames, t = [], 0.0
    for family, pts in FLOW_ROUTES:
        c = d.accent(family)
        frames.append((t, pts[0], 0, c))
        t += fade
        frames.append((t, pts[0], 1, c))
        for a, b in zip(pts, pts[1:]):
            t += math.dist(a, b) / speed
            frames.append((t, b, 1, c))
        t += fade
        frames.append((t, pts[-1], 0, c))
        t += pause
    total = t
    keys = "".join(f"{100 * s / total:.3f}%{{transform:translate({x}px,{y}px);opacity:{o};fill:{c}}}" for s, (x, y), o, c in frames)
    d.style = (f".token{{animation:fact {total:.2f}s linear infinite;opacity:0}}@keyframes fact{{{keys}}}"
               "@media (prefers-reduced-motion: reduce){.token{animation:none}}")
    d.add(f'<circle class="token" r="7" cx="0" cy="0" stroke="{d.t["bg"]}" stroke-width="2"/>')


VOCABULARY = [
    ("Intent", "The user did something. Only the UI sends it."),
    ("Signal", "The world did something: a work finished, another screen returned a result, the lifecycle moved."),
    ("Fact", "An intent or a signal, the only thing that enters the runtime."),
    ("Capability", "A pure function (slice, fact) → decision for one user scenario."),
    ("Slice", "The state of one capability, the memory of the screen."),
    ("Work", "Async work described as data, with a key and a cancellation policy. The runtime runs it."),
    ("Effect", "A request to the outside world as data: navigate, show a snackbar, share."),
    ("Slot", "Renders exactly one slice and sends intents."),
    ("Host", "Assembles slices, intents, and effects. It holds no product logic."),
]


def vocabulary(theme):
    cols, cw, gap, pad, x0, y0 = 3, 296, 16, 18, 20, 20
    rows = [VOCABULARY[i:i + cols] for i in range(0, len(VOCABULARY), cols)]
    heights = [max(54 + 19 * len(wrap(text, 13, cw - 2 * pad)) for _, text in row) for row in rows]
    w = x0 * 2 + cols * cw + (cols - 1) * gap
    h = y0 * 2 + sum(heights) + gap * (len(rows) - 1)
    d = Drawing(theme, w, h, "The vocabulary of Capability Slice Architecture",
                "Nine terms: " + " ".join(f"{term}: {text}" for term, text in VOCABULARY))
    y = y0
    for row, rh in zip(rows, heights):
        for i, (term, text) in enumerate(row):
            x = x0 + i * (cw + gap)
            accent = d.accent(ENTITY[term])
            d.rect(x, y, cw, rh, fill=d.t["card"], stroke=d.t["border"], rx=8, sw=1)
            d.rect(x, y + 10, 4, rh - 20, fill=accent, rx=2)
            d.text(x + pad, y + 30, term, 16, accent, bold=True)
            for j, line in enumerate(wrap(text, 13, cw - 2 * pad)):
                d.text(x + pad, y + 54 + j * 19, line, 13, d.t["muted"])
        y += rh + gap
    return d


RULES = [
    ("Slice by scenario", "Never by layout block. A capability owns one user scenario, even when it spans several blocks on screen."),
    ("The host assembles, it doesn’t think", "No product conditions in the UI entry point. It connects slices, intents, and effects."),
    ("The runtime is the only bus", "A capability never imports or calls another one. It reacts to the signals the other one sends."),
    ("Effects are the only impurity", "Navigation, snackbars, and analytics leave the logic as data, and the edge performs them."),
    ("Keep the decider small", "About 150 lines or 12 facts. Past that, split the capability."),
]


def rules(theme):
    w, x0, y0, rh, gap = 860, 20, 20, 64, 12
    h = y0 * 2 + len(RULES) * rh + (len(RULES) - 1) * gap
    d = Drawing(theme, w, h, "The five rules of Capability Slice Architecture",
                " ".join(f"{i}. {title}: {text}" for i, (title, text) in enumerate(RULES, 1)))
    for i, (title, text) in enumerate(RULES):
        y = y0 + i * (rh + gap)
        d.rect(x0, y, w - 2 * x0, rh, fill=d.t["card"], stroke=d.t["border"], rx=8, sw=1)
        d.add(f'<circle cx="{x0 + 34}" cy="{y + rh / 2}" r="16" fill="{RUNTIME_SOLID[theme]}"/>')
        d.text(x0 + 34, y + rh / 2 + 6, str(i + 1), 16, d.t["on_solid"], bold=True, anchor="middle")
        d.text(x0 + 66, y + 27, title, 16, bold=True)
        if tw(text, 13) > w - 2 * x0 - 86:
            raise SystemExit(f"rules: “{text}” is too long for one line")
        d.text(x0 + 66, y + 48, text, 13, d.t["muted"])
    return d


def heart(d, x, y, color, fill="none"):
    d.add(f'<path d="M{x} {y + 3} C{x} {y - 1} {x + 6} {y - 1} {x + 6} {y + 3} C{x + 6} {y - 1} {x + 12} {y - 1} {x + 12} {y + 3} '
          f'C{x + 12} {y + 7} {x + 7} {y + 9} {x + 6} {y + 11} C{x + 5} {y + 9} {x} {y + 7} {x} {y + 3}Z" fill="{fill}" stroke="{color}" stroke-width="1.4"/>')


def phone(d, x, y):
    """A wireframe screen: search, a timer banner, three cards with a like button, a comment form.
    Returns the regions as name -> list of (x, y, w, h)."""
    t = d.t
    d.rect(x, y, 190, 400, fill=t["card"], stroke=t["border"], rx=22)
    d.rect(x + 70, y + 10, 50, 5, fill=t["border"], rx=2.5)
    ix, iw = x + 14, 162
    regions = {}
    d.rect(ix, y + 26, iw, 28, fill=t["bg"], stroke=t["border"], rx=14, sw=1)
    d.text(ix + 14, y + 44, "Search", 12, t["muted"])
    regions["search"] = [(ix, y + 26, iw, 28)]
    d.rect(ix, y + 64, iw, 30, fill=t["bg"], stroke=t["border"], rx=6, sw=1)
    d.text(ix + 10, y + 83, "Offer ends in 04:59", 12, t["muted"])
    regions["timer"] = [(ix, y + 64, iw, 30)]
    hearts = []
    for i in range(3):
        cy = y + 104 + i * 58
        d.rect(ix, cy, iw, 50, fill=t["bg"], stroke=t["border"], rx=6, sw=1)
        d.rect(ix + 10, cy + 12, 96, 8, fill=t["border"], rx=4)
        d.rect(ix + 10, cy + 28, 64, 8, fill=t["border"], rx=4)
        heart(d, ix + iw - 26, cy + 19, t["muted"])
        hearts.append((ix + iw - 31, cy + 13, 22, 24))
    regions["results"] = [(ix, y + 104, iw, 166)]
    regions["like"] = hearts
    d.rect(ix, y + 290, 110, 30, fill=t["bg"], stroke=t["border"], rx=6, sw=1)
    d.text(ix + 10, y + 309, "Comment", 12, t["muted"])
    d.rect(ix + 118, y + 290, 44, 30, fill=t["border"], rx=6)
    d.text(ix + 140, y + 309, "Send", 12, t["fg"], anchor="middle")
    regions["form"] = [(ix, y + 290, iw, 30)]
    return regions


SPLIT = [  # capability, what its slice holds
    ("search", "query"),
    ("timer", "seconds left"),
    ("results", "items, loading"),
    ("like", "liked items"),
    ("form", "text, sending"),
]


def screen_split(theme):
    d = Drawing(theme, 1000, 520, "One screen before and after slicing it into capabilities",
                "Before: one class owns the whole screen, so the search, the timer, the list, the likes, the form, navigation, "
                "and analytics share one piece of code. After: five capabilities, search, timer, results, like, and form, "
                "each with its own slice. The like capability covers the like button of every card.")
    t = d.t
    # Before
    d.text(20, 34, "Before", 16, bold=True)
    d.text(20 + tw("Before", 16, True) + 8, 34, "one class owns the screen", 14, t["muted"])
    regions = phone(d, 20, 60)
    bx, by, bw, bh = 290, 110, 190, 270
    jobs = ["loads the list", "searches", "likes an item", "counts down", "checks the form", "navigates", "sends analytics"]
    for name, rects in regions.items():
        for rx_, ry, rw, rh_ in rects:
            if name == "like":
                continue
            d.path([(rx_ + rw, ry + rh_ / 2), (bx, by + bh / 2)], arrow=False, sw=1)
    for rx_, ry, rw, rh_ in regions["like"]:
        d.path([(rx_ + rw - 4, ry + rh_ / 2), (bx, by + bh / 2)], arrow=False, sw=1)
    d.rect(bx, by, bw, bh, fill=t["card"], stroke=t["danger"], stroke_opacity="0.7")
    d.text(bx + 18, by + 32, "Screen logic", 16, bold=True)
    for i, job in enumerate(jobs):
        d.text(bx + 18, by + 62 + i * 27, job, 13, t["muted"])
    d.text(20, 498, "Every change touches code of another scenario.", 13, t["muted"])
    # After
    ox = 520
    d.add(f'<path d="M500 24 L500 496" stroke="{t["border"]}" stroke-width="1"/>')
    d.text(ox, 34, "After", 16, bold=True)
    d.text(ox + tw("After", 16, True) + 8, 34, "a capability per scenario", 14, t["muted"])
    regions = phone(d, ox, 60)
    cap = d.accent("capability")
    for name, rects in regions.items():
        for rx_, ry, rw, rh_ in rects:
            d.rect(rx_ - 3, ry - 3, rw + 6, rh_ + 6, stroke=cap, rx=8, sw=1.5, dash="4 3")
    cx, cw, ch = ox + 262, 200, 46
    centers = {"search": 100, "timer": 160, "results": 220, "like": 290, "form": 365}
    for name, holds in SPLIT:
        cy = centers[name]
        d.rect(cx, cy - ch / 2, cw, ch, fill=cap, fill_opacity=t["tint"], stroke=cap, stroke_opacity="0.7", rx=8)
        d.text(cx + 14, cy - 3, name, 14, cap, bold=True)
        d.text(cx + 14, cy + 14, "slice: " + holds, 12, t["muted"])
        for rx_, ry, rw, rh_ in regions[name]:
            sx = rx_ + rw + 3
            sy = ry + rh_ / 2 if name != "results" else ry + 18
            d.path([(sx, sy), (cx, cy)], color=cap, arrow=False, sw=1)
    d.text(ox, 498, "Each scenario owns its slice. The like covers every card.", 13, t["muted"])
    return d


POLICIES = [
    ("Latest", "A new start cancels the running work.", [(0, 2, "cancel"), (2, 4, "cancel"), (4, 7.5, "done")], 1),
    ("KeepExisting", "A start is ignored while the work runs.", [(0, 6, "done"), (2, None, "ignored"), (4, None, "ignored")], 1),
    ("Parallel", "Every start runs beside the others.", [(0, 5, "done"), (2, 6.5, "done"), (4, 8.5, "done")], 3),
]


def work_policies(theme):
    lx, x0, u, w = 20, 210, 66, 900
    lane, top = 24, 70
    heights = [max(56 + lanes * lane, 76 + 18 * len(wrap(text, 13, x0 - lx - 40))) for _, text, _, lanes in POLICIES]
    h = top + sum(heights) + 50
    d = Drawing(theme, w, h, "Three policies for a work started again under the same key",
                "Starts at three moments under one key. Latest cancels the running work and runs the newest. "
                "KeepExisting ignores new starts while a work runs. Parallel runs every start, and each one answers with a signal.")
    t, work = d.t, d.accent("work")
    # legend
    lgx = x0
    d.add(f'<path d="M{lgx} 24 L{lgx + 12} 24 L{lgx + 6} 33Z" fill="{t["fg"]}"/>')
    d.text(lgx + 18, 33, "start", 13, t["muted"])
    lgx += 70
    d.rect(lgx, 22, 28, 12, fill=work, fill_opacity="0.35", stroke=work, rx=3, sw=1)
    d.text(lgx + 36, 33, "work runs", 13, t["muted"])
    lgx += 124
    d.rect(lgx, 22, 28, 12, fill=t["line"], fill_opacity="0.25", stroke=t["line"], rx=3, sw=1, dash="3 2")
    d.cross(lgx + 28, 28, 5)
    d.text(lgx + 42, 33, "cancelled", 13, t["muted"])
    lgx += 124
    d.add(f'<circle cx="{lgx + 6}" cy="28" r="6" fill="{work}"/>')
    d.text(lgx + 18, 33, "signal", 13, t["muted"])
    lgx += 80
    d.add(f'<path d="M{lgx} 24 L{lgx + 12} 24 L{lgx + 6} 33Z" fill="none" stroke="{t["muted"]}" stroke-width="1.3"/>')
    d.text(lgx + 18, 33, "ignored", 13, t["muted"])

    y = top
    for (name, text, runs, lanes), rh in zip(POLICIES, heights):
        d.rect(lx, y, w - 2 * lx, rh - 10, fill=t["card"], stroke=t["border"], rx=8, sw=1)
        d.text(lx + 16, y + 30, name, 16, bold=True)
        for j, line in enumerate(wrap(text, 13, x0 - lx - 40)):
            d.text(lx + 16, y + 52 + j * 18, line, 13, t["muted"])
        lane_i = 0
        for start, end, kind in runs:
            sx = x0 + start * u
            if kind == "ignored":
                d.add(f'<path d="M{sx - 6} {y + 14} L{sx + 6} {y + 14} L{sx} {y + 23}Z" fill="none" stroke="{t["muted"]}" stroke-width="1.3"/>')
                continue
            d.add(f'<path d="M{sx - 6} {y + 14} L{sx + 6} {y + 14} L{sx} {y + 23}Z" fill="{t["fg"]}"/>')
            by = y + 32 + lane_i * lane
            ex = x0 + end * u
            if kind == "cancel":
                d.rect(sx, by, ex - sx, 14, fill=t["line"], fill_opacity="0.25", stroke=t["line"], rx=3, sw=1, dash="3 2")
                d.cross(ex, by + 7, 5)
            else:
                d.rect(sx, by, ex - sx, 14, fill=work, fill_opacity="0.35", stroke=work, rx=3, sw=1)
                d.add(f'<circle cx="{ex + 10}" cy="{by + 7}" r="6" fill="{work}"/>')
            if lanes > 1:
                lane_i += 1
        y += rh
    # time axis
    ay = y + 4
    d.path([(x0, ay), (x0 + 10 * u, ay)], color=t["line"], sw=1.2)
    d.text(x0 + 10 * u, ay + 22, "time", 13, t["muted"], anchor="end")
    return d


def boundaries(theme):
    d = Drawing(theme, 980, 576, "Boundaries: ports, wiring, and how screens talk",
                "Top: a capability calls its ports, plain functions. The wiring builds the ports from real code: a repository, "
                "a use case, a platform API. Middle: on one screen, the timer capability sends a signal, and the runtime hands it "
                "to the results and banner capabilities. The timer never imports or calls them. Bottom: screens share no runtime. "
                "A work on screen A publishes to a shared source, and screen B reads it through a port and turns it into a signal.")
    t, cap = d.t, d.accent("capability")

    def band(y, title, note):
        d.text(20, y, title, 16, bold=True)
        d.text(20 + tw(title, 16, True) + 10, y, note, 13, t["muted"])

    # 1. Ports and wiring
    band(34, "Ports and wiring", "the capability sees functions, the wiring plugs real code into them")
    y, bh = 64, 64
    d.box(20, y, 200, bh, "capability", "Capability", "knows only its ports")
    d.box(280, y, 190, bh, None, "Ports", "plain functions")
    d.box(530, y, 190, bh, None, "Wiring", "builds the ports")
    d.box(780, y, 180, bh, None, "Real code", "repository, use case")
    my = y + bh / 2
    d.path([(220, my), (278, my)])
    d.text(249, my - 8, "calls", 12, t["muted"], anchor="middle")
    d.path([(530, my), (472, my)])
    d.text(501, my - 8, "builds", 12, t["muted"], anchor="middle")
    d.path([(720, my), (778, my)])
    d.text(749, my - 8, "uses", 12, t["muted"], anchor="middle")

    # 2. Neighbours on one screen
    band(196, "One screen", "neighbours talk through the runtime, never directly")
    cy = 300
    d.box(20, cy - 30, 200, 60, "capability", "timer", "deadline reached", title_size=15)
    d.box(390, cy - 30, 200, 60, None, "Runtime", "queue of facts", solid=True)
    d.box(760, cy - 70, 200, 52, "capability", "results", "drops the item", title_size=15)
    d.box(760, cy + 18, 200, 52, "capability", "banner", "shows the offer", title_size=15)
    d.path([(220, cy), (388, cy)], color=d.accent("work"))
    d.text(304, cy - 8, "Signal", 13, d.accent("work"), anchor="middle")
    d.path([(590, cy - 8), (675, cy - 8), (675, cy - 44), (758, cy - 44)])
    d.path([(590, cy + 8), (675, cy + 8), (675, cy + 44), (758, cy + 44)])
    d.path([(120, cy - 30), (120, 218), (860, 218), (860, cy - 72)], color=t["danger"], dashed=True)
    d.cross(490, 218, 7)
    d.text(504, 211, "never imports or calls", 13, t["danger"])

    # 3. Screens
    band(394, "Between screens", "a shared source in DI, read through a port")
    y, bh = 424, 72
    d.box(20, y, 220, bh, None, "Screen A", "a work publishes")
    d.box(380, y, 220, bh, None, "Shared source", "an event or a state")
    d.box(740, y, 220, bh, None, "Screen B", "a stream → Signal")
    my = y + bh / 2
    d.path([(240, my), (378, my)])
    d.text(309, my - 8, "publish", 12, t["muted"], anchor="middle")
    d.path([(600, my), (738, my)])
    d.text(669, my - 8, "port", 12, t["muted"], anchor="middle")
    d.text(20, 530, "Each screen keeps its own runtime and queue, so the order between screens is not guaranteed.", 13, t["muted"])
    d.text(20, 552, "Keep the flow one way: one publisher per event. A state reaches a screen opened later, an event does not.", 13, t["muted"])
    return d


DIAGRAMS = {
    "flow": flow,
    "flow-animated": lambda theme: flow(theme, animated=True),
    "vocabulary": vocabulary,
    "rules": rules,
    "screen-split": screen_split,
    "work-policies": work_policies,
    "boundaries": boundaries,
}


def main(names):
    unknown = [n for n in names if n not in DIAGRAMS]
    if unknown:
        raise SystemExit(f"unknown diagrams: {', '.join(unknown)}. Known: {', '.join(DIAGRAMS)}")
    OUT.mkdir(parents=True, exist_ok=True)
    for name in names or DIAGRAMS:
        for theme in THEMES:
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(DIAGRAMS[name](theme).svg(), encoding="utf-8")
            print(path.relative_to(OUT.parent.parent))


if __name__ == "__main__":
    main(sys.argv[1:])