"""Builds card.svg: ASCII portrait on the left, neofetch-style card on the right (dark theme).

Run locally with `python generate.py`. With GITHUB_TOKEN set (as in the workflow) the GitHub stats
are fetched live; without it the fallback numbers below are used.

The workflow's own token sees public contributions only. The contribution count therefore needs
STATS_TOKEN, a personal token of this account (read-only); without it the count already on the card
is kept rather than replaced by the public-only number.
"""
import datetime
import json
import os
import re
import urllib.request
from xml.sax.saxutils import escape

USER = "5aadahmad"
# Uptime is age in years. The full birthday comes from the BIRTHDAY secret (YYYY-MM-DD) so it never
# appears in this public repo; without it the age is counted from the birth year alone.
BIRTH_YEAR = 1998
FALLBACK_STATS = {"repos": 4, "stars": 7, "contributions": 3231, "followers": 0}

WIDTH = 66  # characters per info line

# (key, value) rows; None is a blank line, a str is a section header
INFO = [
    ("OS", "Tech Lead"),
    ("Uptime", "{uptime}"),
    ("Host", "Germany"),
    ("Kernel", "Healthcare data & AI platforms"),
    ("IDE", "VS Code"),
    None,
    ("Languages.Programming", "Python, JavaScript, TypeScript, SQL"),
    ("Languages.Computer", "HTML, CSS, JSON, YAML, Markdown"),
    None,
    ("Stack.Backend", "FastAPI, SQLAlchemy, PostgreSQL"),
    ("Stack.Frontend", "React, Vite"),
    ("Stack.AI", "Claude, OpenAI, MCP, RAG, LangGraph"),
    ("Stack.Infra", "Azure, Railway, Docker, Kubernetes, Actions"),
    None,
    ("Building", "TRX Platform"),
    ("Built", "Pulse, Thoughtspace"),
    None,
    ("Hobbies", "Playing guitar, cooking"),
    "Contact",
    ("Website", "saadahmadx.com"),
    ("GitHub", "github.com/5aadahmad"),
    "GitHub Stats",
    ("Repos", "{repos} public"),
    ("Stars", "{stars}"),
    ("Contributions", "{contributions}"),
]

COLORS = {"bg": "#1a0f14",  # IMMOTISS "Real Dark" (CI colour sheet)
           "art": "#c9d1d9", "text": "#c9d1d9", "key": "#ffa657", "value": "#a5d6ff", "dots": "#616e7f"}

ART_X, ART_Y, ART_CELL_W, ART_LINE_H = 20, 28, 4.0, 8.0
INFO_X, INFO_Y, INFO_LINE_H, INFO_FONT = 440, 40, 20, 13.5


def fetch_stats():
    stats_token = os.environ.get("STATS_TOKEN")
    token = stats_token or os.environ.get("GITHUB_TOKEN")
    if not token:
        return FALLBACK_STATS
    query = """query($login: String!) { user(login: $login) {
        followers { totalCount }
        repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) { totalCount nodes { stargazerCount } }
        contributionsCollection { contributionCalendar { totalContributions } } } }"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        u = json.load(r)["data"]["user"]
    contributions = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
    if not stats_token:
        contributions = current_contributions()
    return {
        "repos": u["repositories"]["totalCount"],
        "stars": sum(n["stargazerCount"] for n in u["repositories"]["nodes"]),
        "contributions": contributions,
        "followers": u["followers"]["totalCount"],
    }


def current_contributions():
    """The count on the card now, or the fallback if there is no card yet."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "card.svg"), encoding="utf-8") as f:
            m = re.search(r"Contributions</tspan>.*?class=\"value\">([\d,]+)<", f.read())
        return int(m.group(1).replace(",", ""))
    except (OSError, AttributeError):
        return FALLBACK_STATS["contributions"]


def uptime(today):
    birthday = os.environ.get("BIRTHDAY")
    if birthday:
        born = datetime.date.fromisoformat(birthday)
        years = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    else:
        years = today.year - BIRTH_YEAR
    return f"{years} years"


def info_lines(values):
    """Each line is a list of (css class, text) spans."""
    lines = [[("key", "saad"), ("text", "@"), ("key", "ahmad"), ("text", " " + "─" * (WIDTH - 11))]]
    for row in INFO:
        if row is None:
            lines.append([("text", ".")])
        elif isinstance(row, str):
            lines.append([("text", "")])  # spacer before a section
            lines.append([("text", f"- {row} " + "─" * (WIDTH - len(row) - 3))])
        else:
            key, value = row
            value = value.format(**values)
            dots = WIDTH - len(key) - len(value) - 6
            lines.append([("text", ". "), ("key", key), ("text", ":"),
                          ("dots", " " + "." * max(dots, 1) + " "), ("value", value)])
    return lines


def svg(art, lines):
    c = COLORS
    height = max(ART_Y + len(art) * ART_LINE_H, INFO_Y + len(lines) * INFO_LINE_H) + 20
    art_y = ART_Y + (height - 20 - ART_Y - len(art) * ART_LINE_H) / 2  # centre the portrait vertically
    width = INFO_X + int(WIDTH * INFO_FONT * 0.6) + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,\'DejaVu Sans Mono\',monospace" '
        f'width="{width}px" height="{height:.0f}px" font-size="{INFO_FONT}px">',
        "<style>",
        "@font-face { src: local('Consolas'), local('Consolas Bold'); font-family: 'ConsolasFallback'; "
        "font-display: swap; -webkit-size-adjust: 109%; size-adjust: 109%; }",
        f".key {{fill: {c['key']};}} .value {{fill: {c['value']};}} .dots {{fill: {c['dots']};}} "
        f".text {{fill: {c['text']};}} .art {{fill: {c['art']}; font-size: {ART_CELL_W / 0.6:.2f}px;}} "
        "text, tspan {white-space: pre;}",
        "</style>",
        f'<rect width="{width}px" height="{height:.0f}px" fill="{c["bg"]}" rx="15"/>',
        '<text class="art">',
    ]
    for i, line in enumerate(art):
        if line.strip():
            # textLength pins every row to the same grid whatever monospace font the viewer has
            out.append(f'<tspan x="{ART_X}" y="{art_y + i * ART_LINE_H:.1f}" textLength="{len(line) * ART_CELL_W:.1f}" '
                       f'lengthAdjust="spacingAndGlyphs">{escape(line)}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{INFO_X}" y="{INFO_Y}">')
    for i, spans in enumerate(lines):
        y = INFO_Y + i * INFO_LINE_H
        parts = "".join(f'<tspan class="{cls}">{escape(t)}</tspan>' for cls, t in spans)
        out.append(f'<tspan x="{INFO_X}" y="{y}">{parts}</tspan>')
    out.append("</text>")
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    stats = fetch_stats()
    values = {**{k: f"{v:,}" for k, v in stats.items()}, "uptime": uptime(datetime.date.today())}
    lines = info_lines(values)
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "ascii.txt"), encoding="utf-8") as f:
        art = f.read().rstrip("\n").split("\n")
    with open(os.path.join(here, "card.svg"), "w", encoding="utf-8") as f:
        f.write(svg(art, lines))
    print("stats:", stats)


if __name__ == "__main__":
    main()
