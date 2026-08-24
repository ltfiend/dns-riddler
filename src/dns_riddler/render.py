"""All terminal output lives here (the only module that imports rich)."""

from __future__ import annotations

import string

from rich.console import Console, Group
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from dns_riddler.models import LEVEL_NAMES, Answer, Question, RoundConfig, RoundResult
from dns_riddler.scoring import rank_for


class Renderer:
    def __init__(self, console: Console | None = None):
        self.console = console or Console(highlight=False)

    def banner(self, config: RoundConfig) -> None:
        limit = "unlimited" if config.time_limit is None else f"{config.time_limit:g}s/question"
        cats = ", ".join(config.categories) if config.categories else "all categories"
        self.console.print()
        self.console.print(
            Panel(
                Text.from_markup(
                    "[bold cyan]DNS RIDDLER[/bold cyan]\n"
                    f"[dim]Level: {LEVEL_NAMES[config.level]}  ·  "
                    f"{config.num_questions} questions  ·  {limit}  ·  {cats}[/dim]",
                    justify="center",
                ),
                border_style="cyan",
            )
        )
        self.console.print(
            "[dim]Answer riddles about RFCs, dig output, zone files and packet captures.\n"
            "For multiple choice, answer with the letter; otherwise type a short answer.[/dim]\n"
        )

    def notice(self, msg: str) -> None:
        self.console.print(f"[yellow]note:[/yellow] {msg}")

    def question(
        self,
        num: int,
        total: int,
        q: Question,
        score: int,
        streak: int,
        choices: list[str] | None,
    ) -> None:
        streak_tag = f"  ·  [orange1]🔥 streak {streak}[/orange1]" if streak >= 3 else ""
        self.console.print(
            Rule(
                f"[bold]Question {num}/{total}[/bold]  ·  "
                f"{q.category}  ·  {LEVEL_NAMES[q.level]}  ·  "
                f"score {score}{streak_tag}",
                style="cyan",
            )
        )
        self.console.print(f"\n{q.prompt}\n")
        if q.exhibit:
            self.console.print(
                Panel(Text(q.exhibit, no_wrap=True, overflow="ignore"), border_style="dim")
            )
            self.console.print()
        if choices:
            for i, choice in enumerate(choices):
                self.console.print(f"  [bold]{string.ascii_lowercase[i]})[/bold] {choice}")
            self.console.print()

    def verdict(self, answer: Answer, show_explanation: bool) -> None:
        q = answer.question
        if answer.timed_out:
            self.console.print(
                Panel(f"[red bold]⏰ Time's up![/red bold]  The answer was: [bold]{self._expected(answer)}[/bold]",
                      border_style="red")
            )
        elif answer.correct:
            via = f"  [dim](accepted via {answer.matched_via})[/dim]" if answer.matched_via else ""
            self.console.print(f"[green bold]✔ Correct![/green bold] +{answer.points} points{via}")
        else:
            self.console.print(
                f"[red bold]✘ Not quite.[/red bold]  The answer was: [bold]{self._expected(answer)}[/bold]"
            )
        if show_explanation:
            body: list = [Text(q.explanation)]
            if q.references:
                body.append(Text(f"\nSee: {', '.join(q.references)}", style="dim"))
            self.console.print(Panel(Group(*body), title="[dim]why[/dim]", border_style="blue"))
        self.console.print()

    @staticmethod
    def _expected(answer: Answer) -> str:
        q = answer.question
        if q.answer_type == "choice" and answer.shuffled_choices is not None:
            letter = string.ascii_lowercase[answer.shuffled_answer_index]
            return f"{letter}) {q.correct_display}"
        return q.correct_display

    def summary(self, result: RoundResult, max_score: int) -> None:
        if result.aborted:
            self.console.print("\n[yellow]Round interrupted — partial results:[/yellow]")
        n = len(result.answers)
        pct = 0 if max_score == 0 else round(100 * result.score / max_score)
        best_streak = self._best_streak(result)

        self.console.print(Rule("[bold]Results[/bold]", style="cyan"))
        table = Table(show_lines=False, pad_edge=False)
        table.add_column("#", justify="right", style="dim")
        table.add_column("Category")
        table.add_column("Lvl", justify="center")
        table.add_column("Verdict")
        table.add_column("Your answer", overflow="fold", max_width=30)
        table.add_column("Expected", overflow="fold", max_width=40)
        table.add_column("Pts", justify="right")
        for i, a in enumerate(result.answers, 1):
            if a.timed_out:
                verdict = "[red]⏰ timed out[/red]"
            elif a.correct:
                verdict = "[green]✔ correct[/green]"
            else:
                verdict = "[red]✘ wrong[/red]"
            table.add_row(
                str(i),
                a.question.category,
                str(a.question.level),
                verdict,
                a.given if a.given else "[dim]—[/dim]",
                a.question.correct_display,
                str(a.points),
            )
        self.console.print(table)

        misses = [a for a in result.answers if not a.correct]
        if misses:
            self.console.print("\n[bold]Where it went sideways:[/bold]")
            for i, a in enumerate(result.answers, 1):
                if a.correct:
                    continue
                refs = f" [dim]({', '.join(a.question.references)})[/dim]" if a.question.references else ""
                self.console.print(f"  [red]#{i}[/red] {a.question.explanation}{refs}")

        title, blurb = rank_for(result.score, max_score)
        self.console.print()
        self.console.print(
            Panel(
                Text.from_markup(
                    f"[bold]{result.num_correct}/{n} correct  ·  "
                    f"{result.score}/{max_score} points  ·  {pct}%  ·  "
                    f"best streak {best_streak}[/bold]\n\n"
                    f"[bold cyan]Your rank: {title}[/bold cyan]\n[dim]{blurb}[/dim]",
                    justify="center",
                ),
                border_style="green" if pct >= 60 else "yellow",
                title="[bold]final answer[/bold]",
            )
        )

    @staticmethod
    def _best_streak(result: RoundResult) -> int:
        best = cur = 0
        for a in result.answers:
            cur = cur + 1 if a.correct else 0
            best = max(best, cur)
        return best
