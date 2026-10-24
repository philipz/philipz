#!/usr/bin/env python3
"""Render assets/readout.svg: an animated terminal session where the skills/eval
harness runs a suite named after philipz, followed by a git log --graph of the career.

Task statuses and commit counts come from real GitHub activity. Run with
GITHUB_TOKEN set (the refresh workflow provides one; locally uses `gh auth token` fallback).
Styling and animation technique mirror sjarmak's readout SVG.
"""
import datetime
import json
import os
import subprocess
import urllib.error
import urllib.request

OWNER = "philipz"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    try:
        res = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            TOKEN = res.stdout.strip()
    except Exception:
        pass

MY_NAMES = {"philipz", "philip zheng", "philipzheng"}

CATEGORIES = [
    ("agent tooling & ai", [
        ("philipz", "skills", "agent skills & specs", "v1.0", "owner"),
        ("philipz", "notebooklm_exporter", "export notebooklm notes", "18 stars", "owner"),
        ("philipz", "deepwiki-md-chrome-extension", "deepwiki markdown conv", "11 stars", "owner"),
        ("philipz", "open-ptc-agent", "mcp code execution agent", "poc", "owner"),
        ("philipz", "autoresearch", "autonomous ai research", "demo", "owner"),
    ]),
    ("cloudflare & workers", [
        ("philipz", "uber_payment_poc", "distributed payment poc", "shipped", "owner"),
        ("philipz", "uber_payment_cloudflare_worker", "worker payment orchestr", "poc", "owner"),
        ("philipz", "restate-cloudflare-workers-poc", "restate durable exec", "poc", "owner"),
        ("philipz", "inngest-cloudflare-workers-poc", "inngest workflow engine", "poc", "owner"),
        ("philipz", "node-redlock", "distributed redlock", "shipped", "owner"),
    ]),
    ("architecture & workflow", [
        ("philipz", "spring-modulith-orders", "modulith orders engine", "shipped", "owner"),
        ("philipz", "spring-modular-monolith", "modular monolith pattern", "sample", "owner"),
        ("philipz", "camunda_insurance_sample", "camunda workflow sample", "sample", "owner"),
        ("philipz", "camunda_hazelcast", "camunda hazelcast cache", "sample", "owner"),
    ]),
    ("devops & containers", [
        ("philipz", "docker_practice", "docker & devops guide", "248 stars", "maintainer"),
        ("philipz", "docker_workshop", "coscup docker katacoda", "55 stars", "owner"),
        ("philipz", "docker-nginx-hhvm-wordpress", "containerized stack", "28 stars", "owner"),
        ("philipz", "code-with-quarkus", "remote dev container", "article", "owner"),
    ]),
]

GRAPH = [
    ("* ", "a1b2c3d", " (HEAD -> main) ", "ai agent tooling: skills, autoresearch, open-ptc-agent"),
    ("| *", "f4e3d2c", " (cloudflare-durable) ", "durable execution: workers, restate, inngest pocs"),
    ("|/", "", "", ""),
    ("* ", "7e8d9c0", " ", "software architecture: spring modulith & camunda workflows"),
    ("* ", "5b6a7c8", " ", "distributed systems: redlock, cloudflare worker payments"),
    ("*  ", "3c4d5e6", " ", "merge devops-era: containers meet enterprise cloud"),
    ("|\\", "", "", ""),
    ("| *", "1a2b3c4", " (docker-pioneer) ", "docker practice & katacoda workshop (COSCUP)"),
    ("|/", "", "", ""),
    ("* ", "9f8e7d6", " ", "open source geek & technical columnist (RunPC/NetAdmin)"),
]

RUNNING_DAYS = 7
W, LH, FS, PAD = 860, 17, 12, 22
CHROME = 34
TYPE_S = 0.031

COLS = {"task": 31, "what": 24, "updated": 8, "commits": 11, "role": 11, "status": 15}


def api(path):
    url = path if path.startswith("http") else f"https://api.github.com{path}"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "philipz-profile-readout")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r), r.headers


def commit_count(owner, name):
    try:
        commits, headers = api(f"/repos/{owner}/{name}/commits?per_page=1")
        link = headers.get("Link", "")
        if 'rel="last"' in link:
            last = [p for p in link.split(",") if 'rel="last"' in p][0]
            return int(last.split("page=")[-1].split(">")[0].split("&")[0])
        return len(commits)
    except Exception:
        return 0


def author_commit_count(owner, name, author):
    try:
        commits, headers = api(f"/repos/{owner}/{name}/commits?author={author}&per_page=1")
        link = headers.get("Link", "")
        if 'rel="last"' in link:
            last = [p for p in link.split(",") if 'rel="last"' in p][0]
            return int(last.split("page=")[-1].split(">")[0].split("&")[0])
        return len(commits)
    except Exception:
        return 0


def repo_activity(owner, name):
    """(days since last push, my commits, total commits)"""
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        meta, _ = api(f"/repos/{owner}/{name}")
        pushed = datetime.datetime.fromisoformat(meta["pushed_at"].replace("Z", "+00:00"))
        total = commit_count(owner, name)
        if meta.get("fork"):
            mine = author_commit_count(owner, name, OWNER)
            if mine == 0:
                mine = 1
        else:
            mine = total
        days = (now - pushed).days
        return days, mine, total
    except Exception as e:
        print(f"warning: failed to get activity for {owner}/{name}: {e}")
        return 999, 0, 0


def updated_str(days):
    if days == 0:
        return "today"
    if days < 365:
        return f"{days}d ago"
    return f"{days // 365}y ago"


def account_counts():
    if not TOKEN:
        return 247, 0
    q = ('query($c:String){user(login:"' + OWNER + '"){repositories(first:100,after:$c,'
         'ownerAffiliations:OWNER,privacy:PUBLIC){pageInfo{hasNextPage endCursor}nodes{isArchived}}}}')
    total = archived = 0
    cursor = None
    try:
        while True:
            body = json.dumps({"query": q, "variables": {"c": cursor}}).encode()
            req = urllib.request.Request("https://api.github.com/graphql", data=body)
            req.add_header("Authorization", f"Bearer {TOKEN}")
            req.add_header("User-Agent", "philipz-profile-readout")
            with urllib.request.urlopen(req, timeout=30) as r:
                page = json.load(r)["data"]["user"]["repositories"]
            total += len(page["nodes"])
            archived += sum(1 for n in page["nodes"] if n["isArchived"])
            if not page["pageInfo"]["hasNextPage"]:
                break
            cursor = page["pageInfo"]["endCursor"]
    except Exception:
        total = 247
    return total, archived


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self):
        self.parts = []
        self.y = CHROME + 28
        self.t = 0.4

    def line(self, tspans, cls="fade", dur=None, nchars=None, gap=1.0):
        style = f"--t:{self.t:.2f}s"
        if cls == "type":
            style += f";--d:{dur:.2f}s;--n:{nchars}"
        body = "".join(f"<tspan class='{c}'>{esc(s)}</tspan>" if c else f"<tspan>{esc(s)}</tspan>"
                       for c, s in tspans)
        self.parts.append(
            f"<text x='{PAD}' y='{self.y}' class='{cls}' style='{style}' xml:space='preserve'>{body}</text>")
        self.y += LH
        self.t += (dur + 0.05) if cls == "type" else 0.09 * gap

    def skip(self, n=1):
        self.y += LH * n


def cell(content, col):
    w = COLS[col]
    if len(content) > w:
        raise ValueError(f"cell overflows {col}({w}): {content!r} is {len(content)} chars")
    return content.ljust(w)


def build_svg(activity, total, archived):
    s = Svg()
    n_tasks = sum(len(rows) for _, rows in CATEGORIES)

    cmd1 = "skills run --suite philipz --oracle tiered"
    s.line([("green", "$ "), ("bright", cmd1)], cls="type", dur=len(cmd1) * TYPE_S, nchars=len(cmd1) + 2)
    s.line([("muted", f"resolving suite ... {n_tasks} tasks in {len(CATEGORIES)} categories, "
                      f"{total} public repos")])
    s.skip()

    border = "+" + "+".join("-" * (w + 1) for w in COLS.values()) + "+"
    blank_cells = ("| " + cell("", "what") + "| " + cell("", "updated") + "| "
                   + cell("", "commits") + "| " + cell("", "role") + "| " + cell("", "status") + "|")
    s.line([("dim", border)], gap=0.5)
    s.line([("muted", "| " + cell("TASK", "task") + "| " + cell("WHAT", "what")
                      + "| " + cell("UPDATED", "updated") + "| " + cell("COMMITS", "commits")
                      + "| " + cell("ROLE", "role") + "| " + cell("STATUS", "status") + "|")], gap=0.5)
    shipped = 0
    for label, rows in CATEGORIES:
        s.line([("dim", border)], gap=0.4)
        s.line([("dim", "| "), ("cyan", cell(label, "task")), ("dim", blank_cells)], gap=0.5)
        for owner, name, what, result, role in rows:
            days_idle, mine, repo_tot = activity[(owner, name)]
            running = days_idle <= RUNNING_DAYS
            if not running:
                shipped += 1
            status = "RUNNING" if running else f"PASS {result}"
            task = name if owner == OWNER else f"{owner}/{name}"
            commits_txt = f"{mine}/{repo_tot}".rjust(COLS["commits"] - 1) + " "
            if len(commits_txt) > COLS["commits"]:
                raise ValueError(f"commits cell overflows: {commits_txt!r}")
            s.line([
                ("dim", "| "), ("link", cell(task, "task")),
                ("dim", "| "), ("", cell(what, "what")),
                ("dim", "| "), ("green" if running else "muted", cell(updated_str(days_idle), "updated")),
                ("dim", "| "), ("bright", commits_txt),
                ("dim", "| "), ("cyan" if role in ("owner", "maintainer") else "muted", cell(role, "role")),
                ("dim", "| "), ("amber" if running else "green", cell(status, "status")), ("dim", "|"),
            ], gap=0.5)
    s.line([("dim", border)], gap=0.5)
    s.line([("green", f"suite result: {n_tasks}/{n_tasks} oracles green "
                      f"({n_tasks - shipped} running, {shipped} shipped)")])
    s.skip()

    s.t += 0.4
    cmd2 = "git log --graph --oneline career"
    s.line([("green", "$ "), ("bright", cmd2)], cls="type", dur=len(cmd2) * TYPE_S, nchars=len(cmd2) + 2)
    for glyphs, sha, ref, msg in GRAPH:
        spans = [("dim", glyphs + " ")]
        if sha:
            spans.append(("orange", sha))
        if ref:
            spans.append(("cyan", ref))
        if msg:
            spans.append(("", msg))
        s.line(spans, gap=0.8)
    s.skip()

    s.line([("muted", "readout auto-refreshed from real commit activity")])
    s.parts.append(
        f"<text x='{PAD}' y='{s.y}' xml:space='preserve'><tspan class='green'>$ </tspan></text>")
    s.parts.append(
        f"<rect x='{PAD + 15}' y='{s.y - FS + 1}' width='7' height='{FS + 2}' class='cursor' "
        f"style='--t:{s.t:.2f}s'/>")
    s.y += LH

    H = s.y + 16
    head = (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
        f"font-family=\"'SF Mono', SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace\" "
        f"role='img' aria-label='Terminal session: skills runs an eval suite named "
        f"philipz over my projects grouped by category, then git log --graph draws "
        f"the career: open source, devops, architecture, and agent tooling'>"
        "<style>"
        f"text {{ font-size: {FS}px; fill: #d0d3da; }}"
        ".dim { fill: #5b5f6b; } .muted { fill: #9aa0ac; } .bright { fill: #eceef2; }"
        ".orange { fill: #d97757; } .green { fill: #3fb950; } .amber { fill: #d29922; }"
        ".link { fill: #79c0ff; } .cyan { fill: #56d4dd; }"
        ".fade { opacity: 0; animation: appear 0.01s linear var(--t) forwards; }"
        ".type { clip-path: inset(0 100% 0 0); animation: typing var(--d) steps(var(--n)) var(--t) forwards; }"
        ".cursor { fill: #3fb950; opacity: 0; animation: blink 1.1s step-end var(--t) infinite; }"
        "@keyframes appear { to { opacity: 1; } }"
        "@keyframes typing { to { clip-path: inset(0 -2% 0 0); } }"
        "@keyframes blink { 0% { opacity: 1; } 50% { opacity: 0; } }"
        "@media (prefers-reduced-motion: reduce) {"
        " .fade, .type, .cursor { animation: none; opacity: 1; clip-path: none; } }"
        "</style>"
        f"<rect width='{W}' height='{H}' rx='10' fill='#16171d' stroke='#2e303a'/>"
        f"<path d='M0 10 a10 10 0 0 1 10 -10 h{W - 20} a10 10 0 0 1 10 10 v24 h-{W} z' fill='#1f2027'/>"
        "<circle cx='22' cy='17' r='6' fill='#ff5f57'/>"
        "<circle cx='42' cy='17' r='6' fill='#febc2e'/>"
        "<circle cx='62' cy='17' r='6' fill='#28c840'/>"
        f"<text x='{W // 2}' y='21' text-anchor='middle' fill='#9aa0ac' font-size='11'>"
        "philipz@taipei: ~/projects</text>"
    )
    return head + "".join(s.parts) + "</svg>"


def main():
    activity = {}
    for _, rows in CATEGORIES:
        for owner, name, _, _, _ in rows:
            activity[(owner, name)] = repo_activity(owner, name)
    total, archived = account_counts()
    svg = build_svg(activity, total, archived)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "readout.svg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(svg)
    n = sum(len(r) for _, r in CATEGORIES)
    print(f"wrote {out}: {n} tasks in {len(CATEGORIES)} categories, {total} public repos")


if __name__ == "__main__":
    main()
