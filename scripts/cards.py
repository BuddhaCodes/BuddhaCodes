#!/usr/bin/env python3
"""Draws the activity cards of the profile README from the GitHub GraphQL API.

    GITHUB_TOKEN=... python3 scripts/cards.py BuddhaCodes          # real data -> assets/*.svg
    python3 scripts/cards.py BuddhaCodes --sample                  # made-up data, to preview the look

The three cards are one small world:
  stats.svg      character sheet: level, XP bar and the five numbers
  languages.svg  skill tree: one branch per language, pips = share of your code
  goban.svg      the contribution calendar as a goban: a stone per active day, touching stones form chains

Standard library only. EXCLUDE_LANGUAGES (comma-separated, e.g. "HTML,CSS") leaves languages out of the tree.
"""
from __future__ import annotations

import datetime as dt
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


def card(width: int, height: int, title: str, body: str, right: str = "") -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(title)}">
  <style>
    .t {{ font: 600 15px {FONT}; fill: {TEXT}; }}
    .r {{ font: 11px {MONO}; fill: {MUTED}; }}
    .n {{ font: 700 24px {FONT}; fill: {TEXT}; }}
    .lv {{ font: 800 40px {FONT}; fill: {GOLD2}; }}
    .l {{ font: 11.5px {MONO}; fill: {MUTED}; }}
    .s {{ font: 13px {FONT}; fill: {TEXT}; }}
    .g {{ font: 11px {MONO}; fill: {GOLD}; }}
    .in {{ opacity: 0; animation: in .6s ease-out forwards; }}
    @keyframes in {{ to {{ opacity: 1; }} }}
    .draw {{ stroke-dasharray: 400; stroke-dashoffset: 400; animation: draw 1s ease-out forwards; }}
    @keyframes draw {{ to {{ stroke-dashoffset: 0; }} }}
    .glow {{ animation: glow 3.2s ease-in-out infinite; }}
    @keyframes glow {{ 50% {{ opacity: .45; }} }}
    @media (prefers-reduced-motion: reduce) {{ .in, .draw, .glow {{ animation: none; opacity: 1; stroke-dashoffset: 0; }} }}
  </style>
  <defs><linearGradient id="dana" x1="0" x2="1"><stop offset="0" stop-color="{PINK}"/><stop offset=".55" stop-color="{ORANGE}"/><stop offset="1" stop-color="{GOLD}"/></linearGradient></defs>
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

    w, h = 520, 188
    bar_x, bar_w = 112, w - 22 - 112
    body = [
        f'  <g class="in"><text class="lv" x="22" y="92">{level}</text>'
        f'<text class="l" x="24" y="110">level</text>'
        f'<text class="l" x="{bar_x}" y="72">xp {human(xp)} · {human(hi - xp)} to level {level + 1}</text>'
        f'<rect x="{bar_x}" y="80" width="{bar_w}" height="8" rx="4" fill="{LINE}"/>'
        f'<rect x="{bar_x}" y="80" width="{max(bar_w * frac, 8):.1f}" height="8" rx="4" fill="url(#dana)"/></g>',
    ]
    items = [(repos["totalCount"], "repos", "▣"), (stars, "stars", "★"), (followers, "followers", "◇"),
             (commits, "commits · 1y", "♥"), (prs, "PRs · 1y", "◆")]
    col = (w - 44) / len(items)
    for i, (value, label, glyph) in enumerate(items):
        x = 22 + col * i + col / 2
        body.append(f'  <g class="in" style="animation-delay:{0.3 + i * 0.08:.2f}s">'
                    f'<text class="g" x="{x:.1f}" y="130" text-anchor="middle">{glyph}</text>'
                    f'<text class="n" x="{x:.1f}" y="154" text-anchor="middle">{human(value)}</text>'
                    f'<text class="l" x="{x:.1f}" y="173" text-anchor="middle">{label}</text></g>')
    return card(w, h, u.get("name") or u["login"], "\n".join(body), "character sheet")


# ---------------------------------------------------------------- skill tree

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
    rows_y = [74 + i * 30 for i in range(len(top))]
    root_y = (rows_y[0] + rows_y[-1]) / 2 if top else 80
    body = [f'  <g class="in"><circle cx="{root_x}" cy="{root_y:.0f}" r="9" fill="{PANEL}" stroke="url(#dana)" stroke-width="2"/>'
            f'<circle class="glow" cx="{root_x}" cy="{root_y:.0f}" r="3.5" fill="{GOLD2}"/></g>']
    node_x, pips_x, pip_w = 128, 300, 17
    for i, (name, (size, color)) in enumerate(top):
        pct = size / total * 100
        y = rows_y[i]
        on = max(1, round(pct / 10))
        r = 4 + 4 * pct / 100
        d = f"M{root_x + 9} {root_y:.0f}C{root_x + 50} {root_y:.0f} {node_x - 50} {y} {node_x - r:.1f} {y}"
        pips = "".join(f'<rect x="{pips_x + k * pip_w}" y="{y - 6}" width="{pip_w - 4}" height="9" rx="2" '
                       f'fill="{color if k < on else LINE}"{"" if k < on else " opacity=\".7\""}/>' for k in range(10))
        body.append(f'  <g style="animation-delay:{i * 0.1:.2f}s" class="in">'
                    f'<path class="draw" d="{d}" fill="none" stroke="{color}" stroke-opacity=".55" stroke-width="1.6"/>'
                    f'<circle cx="{node_x}" cy="{y}" r="{r:.1f}" fill="{color}"/>'
                    f'<text class="s" x="{node_x + 18}" y="{y + 4}">{escape(name)}</text>{pips}'
                    f'<text class="l" x="{w - 22}" y="{y + 4}" text-anchor="end">{pct:.0f}%</text></g>')
    return card(w, 74 + 30 * len(top) + 8, "skill tree", "\n".join(body), "by share of code written")


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

    parts = [f'  <defs><radialGradient id="st" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff"/>'
             f'<stop offset=".6" stop-color="{TEXT}"/><stop offset="1" stop-color="#b5ad9b"/></radialGradient>'
             f'<radialGradient id="hot" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff6d8"/>'
             f'<stop offset=".55" stop-color="{GOLD2}"/><stop offset="1" stop-color="{GOLD}"/></radialGradient></defs>',
             f'  <rect x="{left - 10}" y="{top - 10}" width="{last_x - left + 20}" height="{last_y - top + 20}" rx="4" fill="#151c33"/>']
    grid = [f"M{gx(i)} {top}V{last_y}" for i in range(len(weeks))] + [f"M{left} {gy(j)}H{last_x}" for j in range(7)]
    parts.append(f'  <path d="{" ".join(grid)}" stroke="{GOLD}" stroke-opacity=".16" stroke-width="1"/>')
    for i in range(3, len(weeks), 13):  # star points, like a goban's hoshi
        parts.append(f'  <circle cx="{gx(i)}" cy="{gy(3)}" r="1.8" fill="{GOLD}" fill-opacity=".45"/>')

    # links between touching stones: faint for every chain, gold for the longest one
    soft, hard = [], []
    for (i, j) in stones:
        for n in ((i + 1, j), (i, j + 1)):
            if n in stones:
                seg = f"M{gx(i)} {gy(j)}L{gx(n[0])} {gy(n[1])}"
                (hard if (i, j) in in_big else soft).append(seg)
    if soft:
        parts.append(f'  <path d="{" ".join(soft)}" stroke="{TEXT}" stroke-opacity=".35" stroke-width="1.4" stroke-linecap="round"/>')
    if hard:
        parts.append(f'  <path class="glow" d="{" ".join(hard)}" stroke="{GOLD2}" stroke-width="2.2" stroke-linecap="round"/>')

    seen_month = None
    for i, wk in enumerate(weeks):
        first = dt.date.fromisoformat(wk["contributionDays"][0]["date"])
        if first.month != seen_month:
            seen_month = first.month
            if i < len(weeks) - 2:
                parts.append(f'  <text class="l" x="{gx(i)}" y="{top - 16}" font-size="10">{first.strftime("%b")}</text>')
    for (i, j), (date, count, lv) in sorted(stones.items()):
        r = (2.4, 3.3, 4.2, 5.2)[lv - 1]
        fill = "url(#hot)" if lv == 4 else "url(#st)"
        parts.append(f'  <circle class="in" style="animation-delay:{i * 0.012:.2f}s" cx="{gx(i)}" cy="{gy(j)}" r="{r}" fill="{fill}">'
                     f'<title>{date}: {count}</title></circle>')

    ly = last_y + 30
    parts.append(f'  <text class="l" x="{left - 10}" y="{ly}">every day an intersection · every stone a day with contributions</text>')
    summary = f'{len(stones)} stones · {len(groups)} chains · longest {len(big)}'
    parts.append(f'  <text class="g" x="{last_x + 10}" y="{ly}" text-anchor="end">{summary}</text>')
    return card(int(w), int(h), "contribution goban", "\n".join(parts), f'{cal["totalContributions"]} contributions · last year')


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    login = args[0] if args else os.environ.get("GITHUB_REPOSITORY_OWNER", "BuddhaCodes")
    if "--sample" in sys.argv:
        user = sample(login)
    else:
        token = os.environ.get("GITHUB_TOKEN") or sys.exit("Set GITHUB_TOKEN (or pass --sample).")
        user = fetch(login, token)
    exclude = {x.strip() for x in os.environ.get("EXCLUDE_LANGUAGES", "").split(",") if x.strip()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "stats.svg").write_text(stats_svg(user), encoding="utf-8")
    (OUT / "languages.svg").write_text(languages_svg(user, exclude), encoding="utf-8")
    (OUT / "goban.svg").write_text(goban_svg(user), encoding="utf-8")
    print("wrote", ", ".join(p.name for p in sorted(OUT.glob("*.svg"))))


if __name__ == "__main__":
    main()