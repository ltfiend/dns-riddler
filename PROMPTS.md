## 2026-08-24 03:31:46

using your DNS skill I'd like you to make a DNS riddler game that comes up with DNS questions and gives a sort of quiz.  Maybe it could even be used as an interview tool but let's keep it a little more fun for now.  The riddles should include RFC questions, dig or other dns tool output and questions about the material or maybe a 'what's wrong here', pcaps or other traffic captures asking the user to analyze them and provide input.  Make the game text based, configurable for level of DNS knowledge, number of questions to ask (tool should keep score and give a result to ask) and maybe a time to answer function (unlimited by default).

---

## 2026-08-24 03:36:57

<task-notification>
<task-id>a8358c1afaf70373c</task-id>
<tool-use-id>toolu_01UUyud9nvAqxn9P5aatN4W1</tool-use-id>
<output-file>/tmp/claude-1000/-home-peter-Git-dns-riddler/ac054f33-4f24-4cb2-b573-b1608d654010/tasks/a8358c1afaf70373c.output</output-file>
<status>completed</status>
<summary>Agent "Design DNS quiz game architecture" finished</summary>
<note>A task-notification fires each time this agent stops with no live background children of its own. The user can send it another message and resume it, so the same task-id may notify more than once.</note>
<result>The project directory is empty except for PROMPTS.md (the original prompt notes), so this is a pure greenfield design. Below is the complete implementation plan.

# DNS Riddler — Implementation Plan

## 1. Project layout

Package name `dns-riddler` (import name `dns_riddler`), src-layout, pyproject-based, console entry point `dns-riddler`. Runtime dependency: only `rich`. Everything else is stdlib (`argparse`, `json`, `select`, `difflib`, `random`, `importlib.resources`).

### Recommended file tree

```
/home/peter/Git/dns-riddler/
├── pyproject.toml              # build metadata, deps, entry point, package data
├── README.md                   # usage, docker instructions, screenshots
├── Dockerfile
├── .dockerignore
├── .gitignore
├── PROMPTS.md                  # (existing)
├── src/
│   └── dns_riddler/
│       ├── __init__.py         # __version__
│       ├── __main__.py         # `python -m dns_riddler` -&gt; cli.main()
│       ├── cli.py              # argparse spec, config assembly, main()
│       ├── models.py           # dataclasses: Question, Choice, RoundConfig, Answer, RoundResult
│       ├── bank.py             # load/validate question banks, filter by level/category, sample
│       ├── matching.py         # normalization + alias/regex/fuzzy answer matching
│       ├── timer.py            # timed_input(): select()-based timed stdin read
│       ├── engine.py           # game loop: ask, collect, judge, track state
│       ├── scoring.py          # points, streaks, rank titles
│       ├── render.py           # all rich output: panels, exhibits, summary table
│       └── data/               # bundled question bank (JSON, one file per category)
│           ├── rfc.json
│           ├── tool_output.json
│           ├── capture.json
│           ├── zone_file.json
│           ├── dnssec.json
│           └── troubleshooting.json
└── tests/
    ├── conftest.py
    ├── test_matching.py
    ├── test_bank_schema.py     # validates every shipped question
    ├── test_scoring.py
    └── test_engine.py          # scripted round with injected inputs
```

### Module responsibilities

- **models.py** — plain `@dataclass` types, no logic beyond `from_dict()` construction with validation errors that name the offending question id. No third-party schema lib; hand-rolled validation is enough and keeps deps at just `rich`.
- **bank.py** — loads every `data/*.json` via `importlib.resources` (works installed and in Docker), plus optional external bank dir/file (`--bank`) for interview packs. Validates on load; filters by difficulty and category; samples `n` questions with a seeded `random.Random(seed)` so `--seed` gives reproducible rounds. Shuffles choice order per question (also seeded), tracking the correct index after shuffle.
- **matching.py** — pure functions, fully unit-testable, no I/O.
- **timer.py** — the only place that touches raw stdin/termios behavior; isolates the platform-sensitive code.
- **engine.py** — orchestrates one round; takes a `render` object and an `input_fn` so tests can inject canned answers without a TTY.
- **render.py** — the only module importing `rich`. Question panels, exhibit blocks (`rich.panel.Panel` with `Syntax`/plain monospace text, no wrapping), progress header ("Question 3/10 · Level: Advanced · Score: 45"), verdict lines, end-of-round summary table, rank banner.
- **scoring.py** — pure scoring math and rank lookup.
- **cli.py** — argparse only; builds `RoundConfig`, calls engine, exit codes (0 normal, 2 bad args/bank).

`pyproject.toml`: `[build-system]` with `hatchling` (simplest correct src-layout + package-data story; setuptools also fine), `requires-python = "&gt;=3.10"`, `dependencies = ["rich&gt;=13"]`, `[project.scripts] dns-riddler = "dns_riddler.cli:main"`, optional dev extra `[project.optional-dependencies] dev = ["pytest"]`.

## 2. Question bank format and schema

**Recommendation: JSON**, one file per category. YAML would be nicer to hand-author multiline dig output, but it costs a dependency and parsing ambiguity; JSON is stdlib, and the pain of multiline strings is manageable by allowing `exhibit` to be **either a string or a list of lines** (bank loader joins lists with `\n`). That keeps hand-authoring of dig/tcpdump exhibits pleasant in JSON.

Each file: `{"category": "tool-output", "questions": [ ... ]}`.

### Schema (per question)

```json
{
  "id": "tool-output-014",
  "level": 3,
  "category": "tool-output",
  "tags": ["edns", "truncation"],
  "prompt": "This query was retried over TCP immediately after the response below. Why?",
  "exhibit": [
    "; &lt;&lt;&gt;&gt; DiG 9.18.24 &lt;&lt;&gt;&gt; big.example.com TXT",
    ";; -&gt;&gt;HEADER&lt;&lt;- opcode: QUERY, status: NOERROR, id: 23198",
    ";; flags: qr tc rd ra; QUERY: 1, ANSWER: 0, AUTHORITY: 0, ADDITIONAL: 1",
    ";; OPT PSEUDOSECTION:",
    "; EDNS: version: 0, flags:; udp: 512"
  ],
  "answer_type": "text",
  "choices": null,
  "accept": ["tc bit", "tc flag", "truncated", "truncation", "response was truncated"],
  "accept_regex": ["\\btc\\b.*(set|flag|bit)", "truncat"],
  "answer_display": "The TC (truncated) bit is set, so the client retries over TCP",
  "explanation": "The flags line shows 'tc': the response exceeded the advertised 512-byte EDNS buffer, so the server truncated it and the resolver fell back to TCP per RFC 1035 §4.2.2 / RFC 7766.",
  "references": ["RFC 1035", "RFC 7766"]
}
```

Field rules (enforced by the loader and by `test_bank_schema.py`):

- `id` — unique across the whole bank; convention `&lt;category&gt;-NNN`.
- `level` — int 1–4 (beginner/intermediate/advanced/expert).
- `category` — one of: `rfc`, `tool-output`, `capture`, `zone-file`, `dnssec`, `troubleshooting` (loader accepts the file's category as default so per-question repetition is optional).
- `answer_type` — `"choice"` or `"text"`.
- For `choice`: `choices` is a list of 3–5 strings; `answer_index` (int into the *authored* order — engine shuffles at runtime and remaps); `accept`/`accept_regex` must be null. Player may also type the choice letter or the choice text.
- For `text`: `accept` (list of alias strings, required, non-empty) and optional `accept_regex` (list of regex strings, compiled at load time so bad patterns fail validation). `answer_display` — canonical answer shown in review.
- `explanation` — required for every question (this is the teaching payload); `references` optional list of RFC/doc strings, rendered as a dim footer.
- `exhibit` — optional string or list of lines; rendered verbatim in a bordered monospace panel, never re-wrapped.

**Templating/randomization: keep v1 static.** Reserve it in the schema now — allow `{{var}}` placeholders and an optional `"vars": {"ip": "ipv4", "ttl": "ttl", "domain": "domain"}` field — but the v1 loader simply rejects questions that declare `vars` (explicit "not yet supported" error). Rationale: randomizing exhibits correctly is hard (a randomized IP must stay consistent between the exhibit, the accepted answers, and the explanation), and it multiplies test surface. Static content plus `--seed`-driven sampling/shuffling already gives good replay variety and reproducible interview rounds. Templating is a clean v2 feature since the whole bank flows through one loader function.

## 3. Timer implementation

**Recommendation: `select.select()` on stdin in canonical (line) mode, wrapped in `timer.timed_input(prompt, timeout)`.**

Evaluation of options:

- **`threading` + `input()`** — rejected. A blocked `input()` thread can't be cancelled; after a timeout the stale thread still owns stdin and its eventual read corrupts the next prompt. Known-bad pattern.
- **`signal.alarm` / SIGALRM** — works on Linux and is simple, but signals interact poorly with readline and are impossible on Windows; only one alarm at a time; exception-based flow is clumsy for a countdown.
- **`rich.prompt.Prompt`** — no timeout support at all; it wraps `input()`. Use rich for *printing* the prompt/countdown, not for reading.
- **`select` on stdin** — the right tool. In the terminal's default canonical mode, stdin becomes readable only when the user presses Enter, so `select([sys.stdin], [], [], remaining)` followed by `sys.stdin.readline()` gives a clean full-line timed read with normal echo and line editing. No termios raw-mode fiddling needed.

Concrete design of `timed_input(console, prompt, timeout) -&gt; str | None`:

1. If `timeout is None` or stdin isn't a TTY or `select` is unavailable on the platform (Windows: `select` doesn't work on console handles), fall back to plain `input(prompt)` — timer silently unlimited off-POSIX, documented in README. Linux/macOS are the real targets; Docker covers everyone else.
2. Otherwise print the prompt (with a `[dim](30s)[/]` budget note), then loop: `ready, _, _ = select.select([sys.stdin], [], [], min(1.0, deadline - now))`. On ready → `readline()`, strip, return. On deadline → print a newline + timeout notice, return `None`.
3. The 1-second tick loop exists so a future version can live-update a countdown; **v1 does not redraw a countdown** (mixing `rich.Live` with echoed line input is fragile). Show the budget up front and a "Time's up!" panel on expiry. `None` is scored as incorrect with a distinct "timed out" marker in the summary.
4. One subtlety to handle: after a timeout, the user may still be mid-typing; the engine flushes any pending stdin data (`select` with 0 timeout + `readline`) before the next question so stale input never answers question N+1.

Both multiple-choice input ("a"–"d") and free-text go through the same function, so the timer behaves identically everywhere. The engine receives `input_fn` as a parameter (default `timed_input`), so tests inject a fake.

## 4. Fuzzy matching design

All in `matching.py`, pure functions:

**Normalization** (`normalize(s)`):
1. NFC-normalize, casefold, strip.
2. Collapse internal whitespace runs to single spaces.
3. Strip surrounding punctuation and drop `.,;:!?'"()` (but **keep** characters meaningful in DNS answers: `.` inside tokens for FQDNs/IPs, `-`, `_`, `/`, `=`, `:` for IPv6 — i.e., strip punctuation only at token edges, and drop a single trailing `.` on domain-like tokens so `example.com.` == `example.com`).
4. Drop leading articles ("the ", "a ", "an ") only — no deeper stopword stripping.

**Match pipeline** (`check_text_answer(user, question) -&gt; MatchResult`), in order, short-circuiting:
1. Exact match of `normalize(user)` against `normalize(alias)` for each alias in `accept`.
2. `accept_regex` patterns (compiled with `re.IGNORECASE` at bank-load) via `re.search` against the normalized input. Regex is the escape hatch for structured answers ("rcode 2", "rcode=2", "servfail (2)") and word-order-free acceptance — use it in content only when alias enumeration gets silly.
3. Typo tolerance: `difflib.SequenceMatcher(None, norm_user, norm_alias).ratio() &gt;= 0.85` against each alias, **only when the alias is ≥ 6 characters** (so "SRVFAIL" matches "servfail" but "aaa" can't fuzz into "aaaa" — record-type answers must be exact). Per-question opt-out flag `"fuzzy": false` for questions where near-misses are the whole point.
4. Multiple-choice: accept the letter (`a`/`A`/`a)`), the 1-based number, or normalized full/prefix-unambiguous choice text.

`MatchResult` records *which* rule matched, shown subtly in review ("accepted via alias: 'rcode 2'") — useful in interview mode and for debugging bank content.

## 5. CLI spec

`argparse` (no click — one command, few flags, zero extra deps).

```
dns-riddler [OPTIONS]

  -l, --level {1,2,3,4,beginner,intermediate,advanced,expert}
                        Difficulty tier (default: 2). Pulls questions at that
                        level, backfilling from adjacent levels if the pool
                        after filters is too small (with a notice).
  -n, --questions N     Questions per round (default: 10)
  -t, --time SECONDS    Per-question time limit (default: unlimited)
  -c, --category CAT    Restrict categories; repeatable
                        (rfc, tool-output, capture, zone-file, dnssec,
                        troubleshooting). Default: all.
      --seed SEED       Seed question selection, choice shuffle order
                        (reproducible interview rounds)
      --review {each,end,none}
                        Show explanations after each question (default),
                        only in the final summary, or never (pure quiz mode)
      --bank PATH       Extra question file/dir merged over the built-in bank
      --list-categories List categories with per-level question counts, exit
      --no-color        Plain output (also honors NO_COLOR env var)
  -V, --version / -h, --help
```

Notes: `--review each` is the fun/learning default; `--review end --seed X -t 60` is the interview preset (call that combo out in the README). Category names validated against the loaded bank so `--bank` packs can introduce new categories for free.

## 6. Scoring, results, ranks

Keep it simple, make the summary the star:

- **Points**: base = level × 10 (10/20/30/40). A wrong or timed-out answer scores 0 — no negatives.
- **Streak bonus**: +5 per correct answer while on a streak of 3+, shown as a small flame/lightning marker in the header. One mechanic, easy to explain, adds fun.
- **Speed bonus** only when `--time` is set: +5 if answered in under half the budget. Skip otherwise (don't punish thoughtful play in unlimited mode).
- **Summary screen** (rich table): per-question row — number, category, level, verdict (correct / wrong / timed out), your answer, expected answer; below it the explanation + RFC refs for every miss (and for hits too when `--review end`). Header panel: score, max possible, percentage, best streak.
- **Rank titles** by percentage of max possible — pure lookup table in `scoring.py`:
  - 0–19%: **NXDOMAIN**
  - 20–39%: **Lame Delegation**
  - 40–59%: **Stub Resolver**
  - 60–74%: **Caching Resolver**
  - 75–89%: **Recursive Resolver**
  - 90–99%: **Authoritative Server**
  - 100%: **Root Server** (rendered with a big rich banner)

## 7. Dockerfile

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
ENV TERM=xterm-256color
ENTRYPOINT ["dns-riddler"]
```

- Single stage is fine — pure-Python, no build toolchain, image stays small. `.dockerignore` excludes `tests/`, `.git`, `__pycache__`, `PROMPTS.md`.
- README must state the TTY requirement: `docker run -it --rm dns-riddler --level 3 -n 10` (without `-it` there's no interactive stdin and rich degrades). Args after the image name flow straight into the ENTRYPOINT, so all CLI flags work unchanged.
- Optional nicety: `-v $PWD/mybank:/bank` + `--bank /bank` for custom interview packs.

## 8. Testing (pytest, local run)

- **test_matching.py** — table-driven cases for normalization edge cases (trailing dot, case, IPv6 colons, "rcode 2"/"RCODE=2"), alias hits, regex hits, fuzzy threshold boundaries (both sides), short-alias exactness, choice letter/number/text acceptance.
- **test_bank_schema.py** — loads the real shipped bank and asserts every question: unique ids, valid level/category/answer_type, choice questions have 3–5 choices with in-range `answer_index` and no duplicate choices, text questions have non-empty `accept`, all regexes compile, `explanation` present, exhibit lines contain no tabs (rendering) — this test is the content author's safety net.
- **test_scoring.py** — points per level, streak math, speed bonus gating, rank boundaries (19/20, 99/100).
- **test_engine.py** — run a full round with a stub bank, injected `input_fn` feeding scripted answers (including a `None` timeout), assert final `RoundResult`; verify `--seed` determinism by running twice.
- Timer gets a thin unit test for the fallback path only; the `select` path is exercised manually (documented in README) — not worth a pty harness in v1.

## 9. Content plan

Target **~55 questions for v1**: 12–15 per tier across the 6 categories, weighted toward the fun exhibits:

| Category | L1 | L2 | L3 | L4 | Total |
|---|---|---|---|---|---|
| rfc | 3 | 3 | 3 | 3 | 12 |
| tool-output (dig/drill/kdig/delv) | 4 | 4 | 3 | 3 | 14 |
| capture (tcpdump/tshark text) | 2 | 3 | 3 | 3 | 11 |
| zone-file | 2 | 2 | 2 | 1 | 7 |
| dnssec | 1 | 2 | 3 | 3 | 9 |
| troubleshooting | 1 | 1 | 1 | 1 | 4 |
| **Total** | 13 | 15 | 15 | 14 | **57** |

Content authored by you at implementation time; the schema, validation test, and 2–3 seed questions per category (to prove each answer style: choice, text+alias, text+regex, exhibit rendering) are the engineering deliverable.

## Ordered implementation checklist

1. Scaffold: `pyproject.toml`, `.gitignore`, `src/dns_riddler/{__init__,__main__}.py`, empty `data/` files, `git init`, `pip install -e .[dev]` smoke test of the entry point.
2. `models.py` — dataclasses + `Question.from_dict` with descriptive validation errors.
3. `bank.py` — load bundled JSON via `importlib.resources`, merge `--bank`, validate, filter, seeded sample + choice shuffle.
4. Seed the bank with ~12 questions (2 per category) covering every answer style — enough to develop against.
5. `matching.py` + `test_matching.py` (write tests first here; it's the fiddliest pure logic).
6. `test_bank_schema.py` against the seed bank.
7. `timer.py` — `timed_input` with select path + fallback; manual TTY test.
8. `scoring.py` + `test_scoring.py`.
9. `render.py` — question panel, exhibit panel, verdict, summary table, rank banner.
10. `engine.py` + `cli.py` wiring; `test_engine.py` with injected inputs; verify `--seed` reproducibility and post-timeout stdin flush.
11. `Dockerfile` + `.dockerignore`; verify `docker build` and `docker run -it` including a timed round.
12. Author the full ~57-question bank (schema test keeps you honest); `README.md` with usage, interview-mode recipe, Docker instructions.
13. Polish pass: `--list-categories`, `NO_COLOR`, Ctrl-C handling (graceful partial summary), final playtest at each level.

### Critical Files for Implementation
- /home/peter/Git/dns-riddler/pyproject.toml
- /home/peter/Git/dns-riddler/src/dns_riddler/engine.py
- /home/peter/Git/dns-riddler/src/dns_riddler/matching.py
- /home/peter/Git/dns-riddler/src/dns_riddler/timer.py
- /home/peter/Git/dns-riddler/src/dns_riddler/bank.py</result>
<usage><subagent_tokens>13969</subagent_tokens><tool_uses>1</tool_uses><duration_ms>127750</duration_ms></usage>
</task-notification>

---

## 2026-08-24 07:42:14

prepare this to be checked into github.com/ltfiend/dns-riddler.  I've already created the repo.  Let me know what commands I need to run

---

## 2026-08-25 11:53:22

This is a great start.  See if you can do a deep dive to develop additional questions

---

