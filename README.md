# dns-riddler

A text-based DNS riddle game. It quizzes you with RFC trivia, real-looking `dig`
output to interpret, zone files with subtle bugs, DNSSEC forensics, and
tcpdump-style packet captures to analyze — then scores you and hands you a rank
somewhere between **NXDOMAIN** and **Root Server**.

Fun first, but the `--seed`/`--time`/`--review end` combo makes it a passable
interview screen too.

## Install & run

```bash
pip install .
dns-riddler                    # 10 questions, level 2 (intermediate), untimed
```

Or with Docker (note `-it` — the game needs an interactive TTY):

```bash
docker build -t dns-riddler .
docker run -it --rm dns-riddler --level 3 -n 10
```

## Options

```
-l, --level LEVEL       1-4 or beginner/intermediate/advanced/expert (default: 2)
-n, --questions N       questions per round (default: 10)
-t, --time SECONDS      per-question time limit (default: unlimited)
-c, --category CAT      restrict categories, repeatable:
                        rfc, tool-output, capture, zone-file, dnssec, troubleshooting
    --seed SEED         reproducible question selection & choice order
    --review MODE       each (default) | end | none — when to show explanations
    --bank PATH         extra question .json file or directory, merged in
    --list-categories   show the question inventory and exit
    --no-color          plain output (NO_COLOR is honored too)
```

Answering: multiple choice takes a letter (`a`), number (`1`), or the choice
text. Free-text answers are matched against alias lists with fuzzy tolerance —
`servfail`, `SERVFAIL`, and `rcode 2` all count.

### Examples

```bash
dns-riddler -l 1 -n 5                      # gentle warm-up
dns-riddler -l 4 -c dnssec -c capture      # expert, security-flavored
dns-riddler -t 30                          # 30s per question (speed bonus!)
```

### Interview mode

Same round for every candidate, explanations withheld until the end, one minute
per question:

```bash
dns-riddler --seed 1035 --review end -t 60 -n 12 -l 3
```

With Docker and a custom question pack:

```bash
docker run -it --rm -v "$PWD/mybank:/bank" dns-riddler --bank /bank --seed 1035 --review end
```

## Scoring

- Base points: level × 10
- Streak bonus: +5 per answer while on a 3+ streak
- Speed bonus: +5 for answering in under half the time budget (timed rounds only)

## Custom question banks

Pass `--bank file.json` (or a directory of `.json` files). Format:

```json
{
  "category": "tool-output",
  "questions": [
    {
      "id": "mypack-001",
      "level": 2,
      "prompt": "What's wrong here?",
      "exhibit": ["line one of dig/tcpdump output", "line two"],
      "answer_type": "text",
      "accept": ["lame delegation"],
      "accept_regex": ["lame"],
      "answer_display": "Lame delegation",
      "explanation": "Why the answer is what it is.",
      "references": ["RFC 1912"]
    }
  ]
}
```

`answer_type` is `"text"` (with `accept` aliases + optional `accept_regex`) or
`"choice"` (with 3-5 `choices` + `answer_index`). Categories: `rfc`,
`tool-output`, `capture`, `zone-file`, `dnssec`, `troubleshooting`.

## Notes

- The answer timer uses `select()` on stdin and works on Linux/macOS terminals.
  On platforms without it (e.g. native Windows console), rounds silently run
  untimed — use Docker for timed rounds there.
- Ctrl-C ends the round early and still prints a summary of what you answered.

## Development

```bash
pip install -e '.[dev]'
pytest
```
