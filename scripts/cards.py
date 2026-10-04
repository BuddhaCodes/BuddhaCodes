#!/usr/bin/env python3
"""Draws the activity cards of the profile README from the GitHub GraphQL API.

    GITHUB_TOKEN=... python3 scripts/cards.py BuddhaCodes          # real data → assets/*.svg
    python3 scripts/cards.py BuddhaCodes --sample                  # made-up data, to preview the look

Writes assets/stats.svg, assets/languages.svg and assets/goban.svg (the contribution calendar drawn as a goban:
every day an intersection, every day with contributions a stone). Standard library only.
Environment: EXCLUDE_LANGUAGES (comma-separated, e.g. "HTML,CSS") leaves those out of the language card.
"""
from __future__ import annotations

import datetime as dt
import json
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
    .n {{ font: 700 26px {FONT}; fill: {TEXT}; }}
    .l {{ font: 11.5px {MONO}; fill: {MUTED}; }}
    .s {{ font: 13px {FONT}; fill: {TEXT}; }}
    .g {{ font: 11px {MONO}; fill: {GOLD}; }}
    .in {{ opacity: 0; animation: in .6s ease-out forwards; }}
    @keyframes in {{ to {{ opacity: 1; }} }}
    @media (prefers-reduced-motion: reduce) {{ .in {{ animation: none; opacity: 1; }} }}
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


def stats_svg(u: dict) -> str:
    repos = u["repositories"]
    stars = sum(r["stargazerCount"] for r in repos["nodes"])
    cc = u["contributionsCollection"]
    items = [(repos["totalCount"], "repos"), (stars, "stars"), (u["followers"]["totalCount"], "followers"),
             (cc["totalCommitContributions"], "commits · 1y"), (cc["totalPullRequestContributions"], "PRs · 1y")]
    w, col = 520, (520 - 44) / len(items)
    body = []
    for i, (value, label) in enumerate(items):
        x = 22 + col * i + col / 2
        body.append(f'  <g class="in" style="animation-delay:{i * 0.08:.2f}s">'
                    f'<text class="n" x="{x:.1f}" y="92" text-anchor="middle">{human(value)}</text>'
                    f'<rect x="{x - 14:.1f}" y="102" width="28" height="3" rx="1.5" fill="url(#dana)"/>'
                    f'<text class="l" x="{x:.1f}" y="124" text-anchor="middle">{label}</text></g>')
    return card(w, 146, u.get("name") or u["login"], "\n".join(body), "@" + u["login"])


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
    w, rows = 520, []
    for i, (name, (size, color)) in enumerate(top):
        pct = size / total * 100
        y = 70 + i * 30
        bar = (w - 44) * pct / 100
        rows.append(f'  <g class="in" style="animation-delay:{i * 0.08:.2f}s">'
                    f'<text class="s" x="22" y="{y}">{escape(name)}</text>'
                    f'<text class="l" x="{w - 22}" y="{y}" text-anchor="end">{pct:.1f}%</text>'
                    f'<rect x="22" y="{y + 7}" width="{w - 44}" height="5" rx="2.5" fill="{LINE}"/>'
                    f'<rect x="22" y="{y + 7}" width="{max(bar, 4):.1f}" height="5" rx="2.5" fill="{color}"/></g>')
    return card(w, 70 + 30 * len(top) + 4, "top languages", "\n".join(rows))


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
    parts = [f'  <defs><radialGradient id="st" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff"/>'
             f'<stop offset=".6" stop-color="{TEXT}"/><stop offset="1" stop-color="#b5ad9b"/></radialGradient>'
             f'<radialGradient id="hot" cx=".35" cy=".3" r=".75"><stop offset="0" stop-color="#fff6d8"/>'
             f'<stop offset=".55" stop-color="{GOLD2}"/><stop offset="1" stop-color="{GOLD}"/></radialGradient></defs>',
             f'  <rect x="{left - 10}" y="{top - 10}" width="{last_x - left + 20}" height="{last_y - top + 20}" rx="4" fill="#151c33"/>']
    grid = [f"M{gx(i)} {top}V{last_y}" for i in range(len(weeks))] + [f"M{left} {gy(j)}H{last_x}" for j in range(7)]
    parts.append(f'  <path d="{" ".join(grid)}" stroke="{GOLD}" stroke-opacity=".16" stroke-width="1"/>')
    for i in range(3, len(weeks), 13):  # star points, like a goban's hoshi
        parts.append(f'  <circle cx="{gx(i)}" cy="{gy(3)}" r="1.8" fill="{GOLD}" fill-opacity=".45"/>')
    seen_month = None
    for i, wk in enumerate(weeks):
        first = dt.date.fromisoformat(wk["contributionDays"][0]["date"])
        if first.month != seen_month:
            seen_month = first.month
            if i < len(weeks) - 2:
                parts.append(f'  <text class="l" x="{gx(i)}" y="{top - 16}" font-size="10">{first.strftime("%b")}</text>')
        for d in wk["contributionDays"]:
            j = (dt.date.fromisoformat(d["date"]).weekday() + 1) % 7  # Sunday first, as GitHub draws it
            lv = level(d["contributionCount"])
            if lv:
                r = (2.4, 3.3, 4.2, 5.2)[lv - 1]
                fill = "url(#hot)" if lv == 4 else "url(#st)"
                delay = i * 0.012
                parts.append(f'  <circle class="in" style="animation-delay:{delay:.2f}s" cx="{gx(i)}" cy="{gy(j)}" r="{r}" fill="{fill}">'
                             f'<title>{d["date"]}: {d["contributionCount"]}</title></circle>')
    legend_y = last_y + 30
    parts.append(f'  <text class="l" x="{left - 10}" y="{legend_y}">every day an intersection · every stone a day with contributions</text>')
    lx = last_x - 74
    for k, r in enumerate((2.4, 3.3, 4.2, 5.2)):
        parts.append(f'  <circle cx="{lx + k * 16}" cy="{legend_y - 4}" r="{r}" fill="{"url(#hot)" if k == 3 else "url(#st)"}"/>')
    title_right = f'{cal["totalContributions"]} contributions · last year'
    return card(int(w), int(h), "contribution goban", "\n".join(parts), title_right)


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
