"""Command-line entry point."""

from __future__ import annotations

import argparse
import random
import sys

from rich.console import Console
from rich.table import Table

from dns_riddler import __version__, bank as bank_mod, engine
from dns_riddler.models import CATEGORIES, LEVEL_NAMES, BankError, RoundConfig
from dns_riddler.render import Renderer

_LEVELS = {
    "1": 1, "2": 2, "3": 3, "4": 4,
    "beginner": 1, "intermediate": 2, "advanced": 3, "expert": 4,
}


def _parse_level(value: str) -> int:
    key = value.strip().lower()
    if key not in _LEVELS:
        raise argparse.ArgumentTypeError(
            f"invalid level {value!r} (use 1-4 or beginner/intermediate/advanced/expert)"
        )
    return _LEVELS[key]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dns-riddler",
        description="A text-based DNS riddle game: RFC trivia, dig output forensics, "
                    "and packet-capture analysis.",
    )
    p.add_argument("-l", "--level", type=_parse_level, default=2, metavar="LEVEL",
                   help="difficulty: 1-4 or beginner/intermediate/advanced/expert (default: 2)")
    p.add_argument("-n", "--questions", type=int, default=10, metavar="N",
                   help="number of questions per round (default: 10)")
    p.add_argument("-t", "--time", type=float, default=None, metavar="SECONDS",
                   help="per-question time limit in seconds (default: unlimited)")
    p.add_argument("-c", "--category", action="append", dest="categories", metavar="CAT",
                   help=f"restrict to a category (repeatable): {', '.join(CATEGORIES)}")
    p.add_argument("--seed", type=int, default=None,
                   help="seed question selection and choice shuffling (reproducible rounds)")
    p.add_argument("--review", choices=["each", "end", "none"], default="each",
                   help="show explanations after each question, at the end, or never "
                        "(default: each)")
    p.add_argument("--bank", metavar="PATH", default=None,
                   help="extra question bank .json file or directory, merged with the built-in bank")
    p.add_argument("--list-categories", action="store_true",
                   help="list categories with per-level question counts and exit")
    p.add_argument("--no-color", action="store_true", help="disable colored output")
    p.add_argument("-V", "--version", action="version", version=f"dns-riddler {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console(highlight=False, no_color=args.no_color or None)

    try:
        bank = bank_mod.load_bank(args.bank)
    except BankError as e:
        console.print(f"[red]bank error:[/red] {e}")
        return 2

    if args.list_categories:
        counts = bank_mod.category_counts(bank)
        table = Table(title="Question bank")
        table.add_column("Category")
        for lvl in (1, 2, 3, 4):
            table.add_column(LEVEL_NAMES[lvl], justify="right")
        table.add_column("Total", justify="right")
        for cat in sorted(counts):
            row = counts[cat]
            table.add_row(cat, *(str(row[lvl]) for lvl in (1, 2, 3, 4)), str(sum(row.values())))
        console.print(table)
        return 0

    if args.questions < 1:
        console.print("[red]error:[/red] --questions must be at least 1")
        return 2
    if args.time is not None and args.time <= 0:
        console.print("[red]error:[/red] --time must be positive")
        return 2

    categories = None
    if args.categories:
        valid = {q.category for q in bank}
        categories = [c.strip().lower() for c in args.categories]
        bad = [c for c in categories if c not in valid]
        if bad:
            console.print(
                f"[red]error:[/red] unknown categor{'y' if len(bad) == 1 else 'ies'}: "
                f"{', '.join(bad)} (available: {', '.join(sorted(valid))})"
            )
            return 2

    config = RoundConfig(
        level=args.level,
        num_questions=args.questions,
        time_limit=args.time,
        categories=categories,
        seed=args.seed,
        review=args.review,
    )

    rng = random.Random(args.seed)
    try:
        questions, notices = bank_mod.select_questions(
            bank, config.level, config.num_questions, categories, rng
        )
    except BankError as e:
        console.print(f"[red]error:[/red] {e}")
        return 2

    renderer = Renderer(console)
    renderer.banner(config)
    for notice in notices:
        renderer.notice(notice)

    try:
        engine.run_round(config, questions, renderer, rng=rng)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. So long, and thanks for all the queries.[/yellow]")
        return 130
    return 0
