#!/usr/bin/env python3
"""Draws the activity cards of the profile README from the GitHub GraphQL API.

    GITHUB_TOKEN=... python3 scripts/cards.py BuddhaCodes          # real data -> assets/*.svg
    python3 scripts/cards.py BuddhaCodes --sample --out=/tmp/x     # made-up data, to preview the look

The three cards are one small world:
  stats.svg      character sheet: level, XP bar and the five numbers, rolling up like an odometer
  languages.svg  skill tree: one branch per language; a cosmic ray shoots down each branch and lights its share
  goban.svg      the contribution calendar as a goban: a stone per active day, touching stones form chains,
                 and a Pac-Man that eats the year row by row, with three ghosts on its tail

Everything moves with CSS and SMIL only (no script), so it plays inside GitHub's <img>.
Standard library only. EXCLUDE_LANGUAGES (comma-separated, e.g. "HTML,CSS") leaves languages out of the tree.
"""
from __future__ import annotations

import datetime as dt
import itertools
import json
import math
import os
import random
import sys
import urllib.request
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

INK, PANEL, LINE = "#0a0d19", "#10162b", "#26304f"
TEXT, MUTED, GOLD, GOLD2 = "#ece8de", "#8e93ad", "#d9b45a", "#f0d594"
PINK, ORANGE = "#e2567a", "#f0a040"  # DanaProcessing accents
PAC, CYAN, SCARED = "#ffd84a", "#5fd0e6", "#2747d8"
FONT = "'Segoe UI', 'Helvetica Neue', Ubuntu, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

QUERY = """
query($login: String!) {
  user(login: $login) {
    name login
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name color } } }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } }
    }
  }
}
"""


def fetch(login: str, token: str) -> dict:
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers={
        "Authorization": f"bearer {token}", "Content-Type": "application/json", "User-Agent": "profile-cards"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL errors: {data['errors']}")
    return data["data"]["user"]


def sample(login: str) -> dict:
    rnd = random.Random(7)
    today = dt.date.today()
    start = today - dt.timedelta(days=364 + (today.weekday() + 1) % 7)
    weeks, day = [], start
    while day <= today:
        week = []
        for _ in range(7):
            if day > today:
                break
            busy = rnd.random() < (0.55 if day > today - dt.timedelta(days=60) else 0.18)
            week.append({"date": day.isoformat(), "contributionCount": rnd.choice([1, 2, 3, 5, 8, 13]) if busy else 0})
            day += dt.timedelta(days=1)
        weeks.append({"contributionDays": week})
    langs = [("C#", "#178600", 920000), ("Python", "#3572A5", 61000), ("HTML", "#e34c26", 54000), ("GLSL", "#5686a5", 12000)]
    return {
        "name": login, "login": login, "followers": {"totalCount": 12},
        "repositories": {"totalCount": 6, "nodes": [{"stargazerCount": 3, "languages": {"edges": [
            {"size": s, "node": {"name": n, "color": c}} for n, c, s in langs]}}]},
        "contributionsCollection": {"totalCommitContributions": 812, "totalPullRequestContributions": 4,
            "contributionCalendar": {"totalContributions": sum(d["contributionCount"] for w in weeks for d in w["contributionDays"]), "weeks": weeks}},
    }


def card(width: int, height: int, title: str, body: str, right: str = "", css: str = "", defs: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <style>
    .t {{ font: 600 15px {FONT}; fill: {TEXT}; }}
    .r {{ font: 11px {MONO}; fill: {MUTED}; }}
    .n {{ font: 700 24px {FONT}; fill: {TEXT}; }}
    .lv {{ font: 800 30px {FONT}; fill: {GOLD2}; }}
    .l {{ font: 11.5px {MONO}; fill: {MUTED}; }}
    .s {{ font: 13px {FONT}; fill: {TEXT}; }}
    .g {{ font: 11px {MONO}; fill: {GOLD}; }}
    .in {{ opacity: 0; animation: in .6s ease-out forwards; }}
    @keyframes in {{ to {{ opacity: 1; }} }}
    .draw {{ stroke-dasharray: 400; stroke-dashoffset: 400; animation: draw 1s ease-out forwards; }}
    @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
    .glow {{ animation: glow 3.2s ease-in-out infinite; }}
    @keyframes glow {{ 50% {{ opacity: .45; }} }}
    .roll {{ animation: roll 1.6s cubic-bezier(.12, .75, .2, 1) both; }}
    @keyframes roll {{ from {{ transform: translateY(0); }} }}
    .pop {{ transform-box: fill-box; transform-origin: center; animation: pop .55s cubic-bezier(.3, 1.7, .5, 1) both; }}
    @keyframes pop {{ from {{ transform: scale(0); opacity: 0; }} }}
    .spin {{ animation: spin 26s linear infinite; }}
    .rev {{ animation-direction: reverse; animation-duration: 18s; }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    .tw {{ animation: tw 3s ease-in-out infinite; }}
    @keyframes tw {{ 50% {{ opacity: .08; }} }}
{css}
    @media (prefers-reduced-motion: reduce) {{
      .in, .draw, .glow, .roll, .pop, .spin, .tw, .shine {{ animation: none; opacity: 1; stroke-dashoffset: 0; }}
    }}
  </style>
  <defs><linearGradient id="dana" x1="0" x2="1"><stop offset="0" stop-color="{PINK}"/><stop offset=".55" stop-color="{ORANGE}"/><stop offset="1" stop-color="{GOLD}"/></linearGradient>
    <filter id="blur" filterUnits="userSpaceOnUse" x="0" y="0" width="{width}" height="{height}"><feGaussianBlur stdDeviation="2.2"/></filter>{defs}</defs>
  <rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="10" fill="{PANEL}" stroke="{LINE}"/>
  <text class="t" x="22" y="32">{escape(title)}</text>
  <rect x="22" y="40" width="34" height="2" rx="1" fill="url(#dana)"/>
  <rect x="1" y="1" width="{width - 2}" height="2" rx="1" fill="url(#dana)" opacity=".7"/>
  <text class="r" x="{width - 22}" y="32" text-anchor="end">{escape(right)}</text>
{body}
</svg>
"""


def human(n: int) -> str:
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def num(v: float) -> str:
    return f"{v:.4f}".rstrip("0").rstrip(".")


def times(ts: list[float]) -> str:
    return ";".join(num(t) for t in ts)


_clip = itertools.count()


def odometer(text: str, x: float, y: float, size: float, cls: str, delay: float, dur: float = 1.6,
             anchor: str = "middle", mono: bool = False) -> str:
    """Number that rolls up into place like an odometer: every digit is a clipped strip of 0-9 that scrolls,
    the units spin the most and land last. Other characters (".", "k", "%") just fade in."""
    widths = [size * (0.6 if mono else 0.58 if c.isdigit() else {".": .3, "k": .54, "%": .9}.get(c, .6)) for c in text]
    total = sum(widths)
    x0 = x - {"start": 0, "middle": total / 2, "end": total}[anchor]
    lh = size * 1.4
    cid = f"od{next(_clip)}"
    out = [f'<clipPath id="{cid}"><rect x="{x0 - 3:.1f}" y="{y - size * .95:.1f}" width="{total + 6:.1f}" height="{size * 1.3:.1f}"/></clipPath>'
           f'<g clip-path="url(#{cid})">']
    place = sum(c.isdigit() for c in text)
    cx = x0
    for c, wd in zip(text, widths):
        mid = cx + wd / 2
        if c.isdigit():
            place -= 1  # 0 = units
            idx = 10 * max(0, 2 - place) + int(c)
            strip = "".join(f'<tspan x="{mid:.1f}" y="{y + k * lh:.1f}">{k % 10}</tspan>' for k in range(idx + 1))
            out.append(f'<text class="{cls} roll" text-anchor="middle" style="transform:translateY(-{idx * lh:.1f}px);'
                       f'animation-duration:{dur * (1 - .1 * min(place, 3)):.2f}s;animation-delay:{delay:.2f}s">{strip}</text>')
        else:
            out.append(f'<text class="{cls} in" x="{mid:.1f}" y="{y:.1f}" text-anchor="middle" '
                       f'style="animation-delay:{delay + dur * .5:.2f}s">{escape(c)}</text>')
        cx += wd
    return "".join(out) + "</g>"


# ---------------------------------------------------------------- character sheet

def stats_svg(u: dict) -> str:
    repos = u["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    cc = u["contributionsCollection"]
    commits, prs, followers = cc["totalCommitContributions"], cc["totalPullRequestContributions"], u["followers"]["totalCount"]
    # XP is a weighted sum of real numbers; level L starts at (2(L-1))^2 XP, so levels get slower as you climb.
    xp = commits + 5 * prs + 3 * stars + 2 * followers + 2 * repos["totalCount"]
    level = int(math.sqrt(xp) / 2) + 1
    lo, hi = (2 * (level - 1)) ** 2, (2 * level) ** 2
    frac = (xp - lo) / (hi - lo)

    w, h = 520, 194
    cx, cy = 60, 88  # the level seal
    bar_x = 116
    bar_w = w - 22 - bar_x
    fw = max(bar_w * frac, 8)
    filled = 2.2  # when the XP bar is full and the seal flares
    css = (f"    .shine {{ animation: shine 4.5s ease-in-out {filled + .4}s infinite; }}\n"
           f"    @keyframes shine {{ 0% {{ transform: translateX(0); }} 40%, 100% {{ transform: translateX({fw + 50:.0f}px); }} }}")
    defs = ('<linearGradient id="sheen" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            '<stop offset=".5" stop-color="#fff" stop-opacity=".75"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            f'<clipPath id="xpbar"><rect x="{bar_x}" y="80" width="{fw:.1f}" height="8" rx="4"/></clipPath>')
    spin_at = f'style="transform-origin:{cx}px {cy}px"'
    body = [
        f'  <g class="in"><circle cx="{cx}" cy="{cy}" r="31" fill="{INK}" stroke="{LINE}"/>'
        f'<circle class="spin" {spin_at} cx="{cx}" cy="{cy}" r="31" fill="none" stroke="url(#dana)" stroke-width="2" stroke-dasharray="1 5" stroke-linecap="round"/>'
        f'<circle class="spin rev" {spin_at} cx="{cx}" cy="{cy}" r="25.5" fill="none" stroke="{GOLD}" stroke-opacity=".4" stroke-dasharray="12 5 2 5"/>'
        f'<text class="l" x="{cx}" y="{cy - 12}" text-anchor="middle" font-size="9" letter-spacing="1.5">LV</text></g>',
        "  " + odometer(str(level), cx, cy + 14, 30, "lv", delay=.3, dur=filled - .3),
        f'  <circle cx="{cx}" cy="{cy}" r="31" fill="none" stroke="{GOLD2}" stroke-width="2" opacity="0">'
        f'<animate attributeName="r" values="31;46" begin="{filled}s" dur=".9s" fill="freeze"/>'
        f'<animate attributeName="opacity" values=".9;0" begin="{filled}s" dur=".9s" fill="freeze"/></circle>',
        f'  <g class="in"><text class="l" x="{bar_x}" y="72">xp {human(xp)} · {human(hi - xp)} to level {level + 1}</text>'
        f'<rect x="{bar_x}" y="80" width="{bar_w}" height="8" rx="4" fill="{LINE}"/>'
        f'<rect x="{bar_x}" y="80" width="{fw:.1f}" height="8" rx="4" fill="url(#dana)">'
        f'<animate attributeName="width" values="0;0;{fw:.1f}" keyTimes="0;.14;1" dur="{filled}s" calcMode="spline" '
        f'keySplines="0 0 1 1;.2 .8 .2 1"/></rect>'
        f'<g clip-path="url(#xpbar)"><rect class="shine" x="{bar_x - 50}" y="80" width="50" height="8" fill="url(#sheen)"/></g></g>',
        f'  <circle cx="{bar_x + fw:.1f}" cy="84" r="2" fill="#fff" opacity="0">'
        f'<animate attributeName="r" values="2;11" begin="{filled}s" dur=".7s" fill="freeze"/>'
        f'<animate attributeName="opacity" values="1;0" begin="{filled}s" dur=".7s" fill="freeze"/></circle>',
    ]
    items = [(repos["totalCount"], "repos", "▣"), (stars, "stars", "★"), (followers, "followers", "◇"),
             (commits, "commits · 1y", "♥"), (prs, "PRs · 1y", "◆")]
    col = (w - 44) / len(items)
    for i, (value, label, glyph) in enumerate(items):
        x = 22 + col * i + col / 2
        t = .5 + i * .12
        body.append(f'  <g class="glow" style="animation-delay:{2.5 + i * .64:.2f}s"><text class="g pop" x="{x:.1f}" y="134" '
                    f'text-anchor="middle" style="animation-delay:{t:.2f}s">{glyph}</text></g>'
                    f'{odometer(human(value), x, 160, 24, "n", delay=t, dur=1.7)}'
                    f'<text class="l in" x="{x:.1f}" y="179" text-anchor="middle" style="animation-delay:{t + .2:.2f}s">{label}</text>')
    return card(w, h, u.get("name") or u["login"], "\n".join(body), "character sheet", css, defs)


# ---------------------------------------------------------------- skill tree

def bezier_length(p: list[tuple[float, float]], steps: int = 64) -> float:
    def at(t: float) -> tuple[float, float]:
        m = 1 - t
        return tuple(m ** 3 * p[0][k] + 3 * m * m * t * p[1][k] + 3 * m * t * t * p[2][k] + t ** 3 * p[3][k] for k in (0, 1))
    pts = [at(i / steps) for i in range(steps + 1)]
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


def languages_svg(u: dict, exclude: set[str]) -> str:
    totals: dict[str, list] = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name in exclude:
                continue
            t = totals.setdefault(name, [0, e["node"]["color"] or MUTED])
            t[0] += e["size"]
    top = sorted(totals.items(), key=lambda kv: -kv[1][0])[:5]
    total = sum(v[0] for _, v in top) or 1
    w, root_x = 520, 44
    h = 74 + 30 * len(top) + 8
    rows_y = [74 + i * 30 for i in range(len(top))]
    root_y = (rows_y[0] + rows_y[-1]) / 2 if top else 80

    # a quiet star field: this is where the cosmic rays come from
    rnd = random.Random(u["login"])
    stars = "".join(f'<circle class="tw" cx="{rnd.uniform(10, w - 10):.0f}" cy="{rnd.uniform(50, h - 8):.0f}" r="{rnd.uniform(.4, 1.1):.1f}" '
                    f'fill="{rnd.choice([TEXT, GOLD2, "#9fb4ff"])}" opacity="{rnd.uniform(.25, .7):.2f}" '
                    f'style="animation-delay:-{rnd.uniform(0, 5):.1f}s;animation-duration:{rnd.uniform(2.4, 5.5):.1f}s"/>' for _ in range(42))
    body = [f'  <g>{stars}</g>',
            f'  <g class="in"><circle class="spin" style="transform-origin:{root_x}px {root_y:.0f}px" cx="{root_x}" cy="{root_y:.0f}" r="15" '
            f'fill="none" stroke="{GOLD}" stroke-opacity=".45" stroke-dasharray="2 4"/>'
            f'<circle cx="{root_x}" cy="{root_y:.0f}" r="9" fill="{PANEL}" stroke="url(#dana)" stroke-width="2"/>'
            f'<circle class="glow" cx="{root_x}" cy="{root_y:.0f}" r="3.5" fill="{GOLD2}"/></g>']
    defs = []
    node_x, pips_x, pip_w = 128, 300, 17
    track = 10 * pip_w - 4
    for i, (name, (size, color)) in enumerate(top):
        pct = size / total * 100
        y = rows_y[i]
        by = y - 1.5  # the ray runs through the middle of the pips
        on = max(1, round(pct / 10))
        r = 4 + 4 * pct / 100
        ctrl = [(root_x + 9, root_y), (root_x + 50, root_y), (node_x - 50, y), (node_x - r, y)]
        d = f"M{root_x + 9} {root_y:.0f}C{root_x + 50} {root_y:.0f} {node_x - 50} {y} {node_x - r:.1f} {y}"
        blen = bezier_length(ctrl)
        end_x = pips_x + max(3.0, track * pct / 100)

        # timeline: the first pass is the intro, then the same ray fires again every `period` seconds
        period = 6.5 + .9 * i
        t_comet = .9 + .3 * i          # comet leaves the root
        c_dur = .45                    # ... and reaches the language node
        t_beam = t_comet + c_dur + .05  # beam enters the pips
        b_dur = .25 + .85 * pct / 100  # ... and hits its percentage
        t_hit = t_beam + b_dur
        rep = f'dur="{period}s" repeatCount="indefinite"'

        comet = "".join(
            f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"{flt} '
            f'stroke-dasharray="16 999" stroke-dashoffset="19"><animate attributeName="stroke-dashoffset" '
            f'values="19;{-(blen + 3):.1f};{-(blen + 3):.1f}" keyTimes="0;{num(c_dur / period)};1" begin="{t_comet:.2f}s" {rep}/></path>'
            for stroke, sw, flt in ((color, 6, ' filter="url(#blur)"'), ("#fff", 1.8, "")))
        node_flash = (f'<circle cx="{node_x}" cy="{y}" r="{r:.1f}" fill="none" stroke="{color}" stroke-width="1.5" opacity="0">'
                      f'<animate attributeName="r" values="{r:.1f};{r + 9:.1f};{r + 9:.1f}" keyTimes="0;{num(.5 / period)};1" begin="{t_comet + c_dur:.2f}s" {rep}/>'
                      f'<animate attributeName="opacity" values=".9;0;0" keyTimes="0;{num(.5 / period)};1" begin="{t_comet + c_dur:.2f}s" {rep}/></circle>')

        pips = []
        for k in range(10):
            px = pips_x + k * pip_w
            if k >= on:
                pips.append(f'<rect x="{px}" y="{y - 6}" width="{pip_w - 4}" height="9" rx="2" fill="{LINE}" opacity=".7"/>')
                continue
            lit = t_beam + b_dur * min(1.0, (k * pip_w + 6.5) / (end_x - pips_x))
            ign = lit + .35
            pips.append(f'<rect x="{px}" y="{y - 6}" width="{pip_w - 4}" height="9" rx="2" fill="{color}">'
                        f'<animate attributeName="fill" values="{LINE};{LINE};#fff;{color}" keyTimes="0;{num(lit / ign)};{num((lit + .06) / ign)};1" dur="{ign:.2f}s"/></rect>'
                        f'<rect x="{px}" y="{y - 6}" width="{pip_w - 4}" height="9" rx="2" fill="#fff" opacity="0">'
                        f'<animate attributeName="opacity" values="0;.7;0;0" keyTimes="0;{num(.06 / period)};{num(.45 / period)};1" begin="{lit + period:.2f}s" {rep}/></rect>')

        cid = f"ray{i}"
        defs.append(f'<linearGradient id="streak{i}" x1="0" x2="1"><stop offset="0" stop-color="{color}" stop-opacity="0"/>'
                    f'<stop offset=".7" stop-color="{color}"/><stop offset="1" stop-color="#fff"/></linearGradient>'
                    f'<clipPath id="{cid}"><rect x="{pips_x - 1}" y="{y - 14}" width="{track + 40}" height="26"/></clipPath>')
        kt = f'keyTimes="0;{num(b_dur / period)};1"'
        fade = f'<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;{num(b_dur / period)};{num((b_dur + .15) / period)};1" begin="{t_beam:.2f}s" {rep}/>'
        # hidden (opacity 0) until it first fires, and parked out of the clip so nothing peeks in
        beam = (f'<g clip-path="url(#{cid})">'
                + "".join(f'<rect x="{pips_x - 70}" y="{by - sh / 2:.1f}" width="70" height="{sh}" rx="{sh / 2}" fill="url(#streak{i})" opacity="0"{flt}>'
                          f'<animate attributeName="x" values="{pips_x - 70};{end_x - 70:.1f};{end_x - 70:.1f}" {kt} begin="{t_beam:.2f}s" {rep}/>{fade}</rect>'
                          for sh, flt in ((8, ' filter="url(#blur)"'), (3, "")))
                + "".join(f'<circle cx="{pips_x - 20}" cy="{by}" r="{cr}" fill="{cf}" opacity="0"{flt}>'
                          f'<animate attributeName="cx" values="{pips_x - 20};{end_x:.1f};{end_x:.1f}" {kt} begin="{t_beam:.2f}s" {rep}/>{fade}</circle>'
                          for cr, cf, flt in ((6, color, ' filter="url(#blur)"'), (2.6, "#fff", ""))) + '</g>')
        impact = (f'<circle cx="{end_x:.1f}" cy="{by}" r="1" fill="none" stroke="#fff" stroke-width="1.5" opacity="0">'
                  f'<animate attributeName="r" values="1;13;13" keyTimes="0;{num(.55 / period)};1" begin="{t_hit:.2f}s" {rep}/>'
                  f'<animate attributeName="opacity" values="1;0;0" keyTimes="0;{num(.55 / period)};1" begin="{t_hit:.2f}s" {rep}/></circle>'
                  f'<g opacity="0"><set attributeName="opacity" to="1" begin="{t_hit:.2f}s" fill="freeze"/>'
                  f'<line class="glow" x1="{end_x:.1f}" x2="{end_x:.1f}" y1="{y - 9}" y2="{y + 6}" stroke="{color}" stroke-width="4" filter="url(#blur)"/>'
                  f'<line x1="{end_x:.1f}" x2="{end_x:.1f}" y1="{y - 9}" y2="{y + 6}" stroke="{GOLD2}" stroke-width="1.5" stroke-linecap="round"/></g>')

        body.append(f'  <g style="animation-delay:{i * 0.1:.2f}s" class="in">'
                    f'<path class="draw" d="{d}" fill="none" stroke="{color}" stroke-opacity=".55" stroke-width="1.6"/>'
                    f'<circle cx="{node_x}" cy="{y}" r="{r:.1f}" fill="{color}"/>'
                    f'<text class="s" x="{node_x + 18}" y="{y + 4}">{escape(name)}</text>{"".join(pips)}</g>')
        body.append(f'  <g>{comet}{node_flash}{beam}{impact}'
                    f'{odometer(f"{pct:.0f}%", w - 22, y + 4, 11.5, "l", delay=t_beam, dur=b_dur + .35, anchor="end", mono=True)}</g>')
    return card(w, h, "skill tree", "\n".join(body), "by share of code written", defs="".join(defs))


# ---------------------------------------------------------------- goban

def chains(stones: set[tuple[int, int]]) -> list[list[tuple[int, int]]]:
    """Connected groups of stones, as in Go: orthogonal neighbours belong to the same chain."""
    seen, out = set(), []
    for s in sorted(stones):
        if s in seen:
            continue
        group, todo = [], [s]
        seen.add(s)
        while todo:
            a, b = todo.pop()
            group.append((a, b))
            for n in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                if n in stones and n not in seen:
                    seen.add(n)
                    todo.append(n)
        out.append(group)
    return out


def scared_timeline(eaten: list[float], period: float, frightened: float = 3.0, warn: float = .9) -> list[tuple[float, str]]:
    """When a ghost is normal (n), frightened blue (b) or blinking white because it is about to recover (w)."""
    spans: list[list[float]] = []
    for t in sorted(max(0.0, t) for t in eaten):
        if spans and t <= spans[-1][1]:
            spans[-1][1] = t + frightened
        else:
            spans.append([t, t + frightened])
    out = [(0.0, "n")]
    for start, end in spans:
        end = min(end, period - .05)
        out.append((start, "b"))
        t, flip = end - warn, "w"
        while t < end:
            if t > start:
                out.append((t, flip))
            flip = "b" if flip == "w" else "w"
            t += .15
        out.append((end, "n"))
    clean: dict[float, str] = {}
    for t, s in out:
        clean[round(t / period, 4)] = s
    return sorted(clean.items())


def goban_svg(u: dict) -> str:
    cal = u["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    cell, left, top = 13, 40, 84
    w = left + cell * (len(weeks) - 1) + 30
    h = top + cell * 6 + 44
    counts = sorted(d["contributionCount"] for wk in weeks for d in wk["contributionDays"] if d["contributionCount"] > 0)

    def level(c: int) -> int:
        if c <= 0 or not counts:
            return 0
        q = [counts[int(len(counts) * f)] for f in (0.25, 0.5, 0.75)]
        return 1 + sum(c > x for x in q)

    gx = lambda i: left + i * cell
    gy = lambda j: top + j * cell
    last_x, last_y = gx(len(weeks) - 1), gy(6)

    stones: dict[tuple[int, int], tuple[str, int, int]] = {}  # (week, weekday) -> (date, count, level)
    for i, wk in enumerate(weeks):
        for d in wk["contributionDays"]:
            j = (dt.date.fromisoformat(d["date"]).weekday() + 1) % 7  # Sunday first, as GitHub draws it
            lv = level(d["contributionCount"])
            if lv:
                stones[(i, j)] = (d["date"], d["contributionCount"], lv)
    groups = chains(set(stones))
    big = max(groups, key=len) if groups else []
    in_big = set(big)
    # the four busiest days are the power pellets, as in the arcade
    pellets = set(sorted(stones, key=lambda s: (-stones[s][1], stones[s][0]))[:4])

    # Pac-Man's route: in from the left, along Sunday, back along Monday... out to the right after Saturday
    xl, xr = left - cell, last_x + cell
    route = [(-16.0, gy(0))]
    for j in range(7):
        x_end = (w + 16 if j == 6 else xr) if j % 2 == 0 else xl
        route.append((x_end, gy(j)))
        if j < 6:
            route.append((x_end, gy(j + 1)))
    seg_start, row_start, run = [], {}, 0.0
    for (ax, ay), (bx, by) in zip(route, route[1:]):
        seg_start.append((run, (bx > ax) - (bx < ax), (by > ay) - (by < ay)))
        if ay == by:
            row_start[int(round((ay - top) / cell))] = (ax, run)
        run += abs(bx - ax) + abs(by - ay)
    path = "M" + "L".join(f"{x:.0f} {y:.0f}" for x, y in route)

    speed = 330.0                   # px per second
    start = 1.8                     # after the stones have faded in
    run_time = run / speed
    lags = (.7, 1.25, 1.8)          # ghosts: Pinky, Inky, Clyde
    respawn = run_time + lags[-1] + .5
    period = respawn + len(weeks) * .02 + 1.4
    arrive = lambda i, j: (row_start[j][1] + abs(gx(i) - row_start[j][0]) - 5) / speed
    rep = f'begin="{start}s" dur="{period:.2f}s" repeatCount="indefinite"'

    css = ("    .blink { animation: blink .5s steps(1) infinite; }\n"
           "    @keyframes blink { 50% { opacity: .35; } }\n"
           f"    .ready {{ font: 700 11px {MONO}; fill: {PAC}; letter-spacing: 2px; }}")
    parts = [f'  <defs><radialGradient id="st" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff"/>'
             f'<stop offset=".6" stop-color="{TEXT}"/><stop offset="1" stop-color="#b5ad9b"/></radialGradient>'
             f'<radialGradient id="hot" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff6d8"/>'
             f'<stop offset=".55" stop-color="{GOLD2}"/><stop offset="1" stop-color="{GOLD}"/></radialGradient></defs>',
             f'  <rect x="{left - 10}" y="{top - 10}" width="{last_x - left + 20}" height="{last_y - top + 20}" rx="4" fill="#151c33"/>']
    grid = [f"M{gx(i)} {top}V{last_y}" for i in range(len(weeks))] + [f"M{left} {gy(j)}H{last_x}" for j in range(7)]
    parts.append(f'  <path d="{" ".join(grid)}" stroke="{GOLD}" stroke-opacity=".16" stroke-width="1"/>')
    for i in range(3, len(weeks), 13):  # star points, like a goban's hoshi
        parts.append(f'  <circle cx="{gx(i)}" cy="{gy(3)}" r="1.8" fill="{GOLD}" fill-opacity=".45"/>')

    # links between touching stones: faint for every chain, gold for the longest one; they fade while the board is eaten
    soft, hard = [], []
    for (i, j) in stones:
        for n in ((i + 1, j), (i, j + 1)):
            if n in stones:
                seg = f"M{gx(i)} {gy(j)}L{gx(n[0])} {gy(n[1])}"
                (hard if (i, j) in in_big else soft).append(seg)
    parts.append(f'  <g><animate attributeName="opacity" values="1;.12;.12;1;1" '
                 f'keyTimes="0;{times([run_time / period, respawn / period, (respawn + 1) / period])};1" {rep}/>')
    if soft:
        parts.append(f'  <path d="{" ".join(soft)}" stroke="{TEXT}" stroke-opacity=".35" stroke-width="1.4" stroke-linecap="round"/>')
    if hard:
        parts.append(f'  <path class="glow" d="{" ".join(hard)}" stroke="{GOLD2}" stroke-width="2.2" stroke-linecap="round"/>')
    parts.append("  </g>")

    seen_month = None
    for i, wk in enumerate(weeks):
        first = dt.date.fromisoformat(wk["contributionDays"][0]["date"])
        if first.month != seen_month:
            seen_month = first.month
            if i < len(weeks) - 2:
                parts.append(f'  <text class="l" x="{gx(i)}" y="{top - 16}" font-size="10">{first.strftime("%b")}</text>')

    eaten_pellets = []
    for (i, j), (date, count, lv) in sorted(stones.items()):
        r = 5.8 if (i, j) in pellets else (2.4, 3.3, 4.2, 5.2)[lv - 1]
        fill = "url(#hot)" if lv == 4 or (i, j) in pellets else "url(#st)"
        a = max(0.0, arrive(i, j))
        back = respawn + i * .02
        eat = (f'<animate attributeName="r" values="{r};{r};0;0;{r * 1.35:.1f};{r};{r}" '
               f'keyTimes="0;{times([a / period, (a + .12) / period, back / period, (back + .15) / period, (back + .3) / period])};1" {rep}/>')
        stone = (f'<circle class="in" style="animation-delay:{i * 0.012:.2f}s" cx="{gx(i)}" cy="{gy(j)}" r="{r}" fill="{fill}">'
                 f'<title>{date}: {count}</title>{eat}</circle>')
        if (i, j) in pellets:
            eaten_pellets.append(a)
            stone = (f'<g class="blink">{stone}</g>'
                     f'<text class="g" x="{gx(i)}" y="{gy(j) - 7}" text-anchor="middle" font-weight="700" opacity="0">+{count}'
                     f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;{times([a / period, (a + .05) / period, (a + .8) / period, (a + 1.2) / period])};1" {rep}/>'
                     f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;0 -12;0 -12" '
                     f'keyTimes="0;{times([a / period, (a + 1.2) / period])};1" {rep}/></text>')
        parts.append("  " + stone)

    # READY! while the board refills, like between arcade levels
    mid_x, mid_y = gx(len(weeks) // 2), gy(3)
    parts.append(f'  <g><rect x="{mid_x - 34}" y="{mid_y - 9}" width="68" height="17" rx="3" fill="{PANEL}" fill-opacity=".85"/>'
                 f'<text class="ready" x="{mid_x}" y="{mid_y + 4}" text-anchor="middle">READY!</text>'
                 f'<animate attributeName="opacity" values="0;1" keyTimes="0;{num(respawn / period)}" calcMode="discrete" {rep}/></g>')

    motion = f'path="{path}" keyPoints="0;1;1" keyTimes="0;{num(run_time / period)};1" calcMode="linear" dur="{period:.2f}s" repeatCount="indefinite"'
    look = {(1, 0): "1.1 0", (-1, 0): "-1.1 0", (0, 1): "0 1.1"}
    pupils = (f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" '
              f'values="{";".join(look[(dx, dy)] for _, dx, dy in seg_start)}" '
              f'keyTimes="{times([s / speed / period for s, _, _ in seg_start])}" dur="{period:.2f}s" repeatCount="indefinite"')
    skirt = ["M-6 0A6 6 0 0 1 6 0V6L4 4.4 2 6 0 4.4-2 6-4 4.4-6 6Z", "M-6 0A6 6 0 0 1 6 0V5L5 6 3 4.4 1 6-1 4.4-3 6-5 4.4-6 5Z"]
    for lag, color in zip(lags, (PINK, CYAN, ORANGE)):
        begin = f'begin="{start + lag:.2f}s"'
        tl = scared_timeline([t - lag for t in eaten_pellets], period)
        kt = f'keyTimes="{";".join(num(t) for t, _ in tl)}" calcMode="discrete" dur="{period:.2f}s" repeatCount="indefinite" {begin}'
        fill = ";".join({"n": color, "b": SCARED, "w": "#e8ecff"}[s] for _, s in tl)
        normal = ";".join("1" if s == "n" else "0" for _, s in tl)
        scared = ";".join("0" if s == "n" else "1" for _, s in tl)
        parts.append(
            f'  <g visibility="hidden"><set attributeName="visibility" to="visible" {begin} fill="freeze"/><animateMotion {motion} {begin}/>'
            f'<path d="{skirt[0]}" fill="{color}"><animate attributeName="d" values="{skirt[0]};{skirt[1]};{skirt[0]}" dur=".3s" repeatCount="indefinite"/>'
            f'<animate attributeName="fill" values="{fill}" {kt}/></path>'
            f'<g><animate attributeName="opacity" values="{normal}" {kt}/>'
            f'<ellipse cx="-2.3" cy="-.6" rx="1.8" ry="2.2" fill="#fff"/><ellipse cx="2.3" cy="-.6" rx="1.8" ry="2.2" fill="#fff"/>'
            f'<g fill="#1d3fbf"><circle cx="-2.3" cy="-.4" r="1"/><circle cx="2.3" cy="-.4" r="1"/>{pupils} {begin}/></g></g>'
            f'<g opacity="0" fill="#ffc6b8" stroke="#ffc6b8"><animate attributeName="opacity" values="{scared}" {kt}/>'
            f'<circle cx="-2" cy="-1" r=".9" stroke="none"/><circle cx="2" cy="-1" r=".9" stroke="none"/>'
            f'<path d="M-4 3.2l1-1 1 1 1-1 1 1 1-1 1 1 1-1" fill="none" stroke-width=".8"/></g></g>')

    mouth = lambda deg: (f"M0 0L{6.8 * math.cos(math.radians(deg)):.2f} {-6.8 * math.sin(math.radians(deg)):.2f}"
                         f"A6.8 6.8 0 1 0 {6.8 * math.cos(math.radians(deg)):.2f} {6.8 * math.sin(math.radians(deg)):.2f}Z")
    parts.append(f'  <g visibility="hidden"><set attributeName="visibility" to="visible" begin="{start}s" fill="freeze"/>'
                 f'<animateMotion {motion} rotate="auto" begin="{start}s"/>'
                 f'<path d="{mouth(42)}" fill="{PAC}"><animate attributeName="d" values="{mouth(42)};{mouth(3)};{mouth(42)}" dur=".24s" repeatCount="indefinite"/></path></g>')

    ly = last_y + 30
    parts.append(f'  <text class="l" x="{left - 10}" y="{ly}">every day an intersection · every stone a day with contributions</text>')
    summary = f'{len(stones)} stones · {len(groups)} chains · longest {len(big)}'
    parts.append(f'  <text class="g" x="{last_x + 10}" y="{ly}" text-anchor="end">{summary}</text>')
    return card(int(w), int(h), "contribution goban", "\n".join(parts), f'{cal["totalContributions"]} contributions · last year', css)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    login = args[0] if args else os.environ.get("GITHUB_REPOSITORY_OWNER", "BuddhaCodes")
    out = next((Path(a[6:]) for a in sys.argv if a.startswith("--out=")), OUT)
    if "--sample" in sys.argv:
        user = sample(login)
    else:
        token = os.environ.get("GITHUB_TOKEN") or sys.exit("Set GITHUB_TOKEN (or pass --sample).")
        user = fetch(login, token)
    exclude = {x.strip() for x in os.environ.get("EXCLUDE_LANGUAGES", "").split(",") if x.strip()}
    out.mkdir(parents=True, exist_ok=True)
    (out / "stats.svg").write_text(stats_svg(user), encoding="utf-8")
    (out / "languages.svg").write_text(languages_svg(user, exclude), encoding="utf-8")
    (out / "goban.svg").write_text(goban_svg(user), encoding="utf-8")
    print("wrote", ", ".join(str(p) for p in sorted(out.glob("*.svg"))))


if __name__ == "__main__":
    main()
