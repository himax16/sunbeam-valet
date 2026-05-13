from datetime import date

from sunbeam_valet.models import TableRow


class MarkdownFormatter:
    def format(self, rows: list[TableRow], round2_count: int) -> str:
        lines = [
            f"**Bug Triage Report** - {date.today().isoformat()}",
            "",
            "| Bug Reference | Summary | Confidence | Agent Votes | Status | Round 2? |",
            "|---|---|---|---|---|---|",
        ]

        for row in rows:
            lines.append(
                f"| [{row.bug_reference}]({row.bug_reference_url}) "
                f"| {row.summary} "
                f"| {_format_confidence(row.confidence)} "
                f"| {_format_agent_votes(row.agent_votes)} "
                f"| {row.status} "
                f"| {_format_round2(row.round2, row.status)} |"
            )

        if round2_count > 0:
            lines.append("")
            lines.append(f"_Round 2 triggered: {round2_count}/{len(rows)} bugs_")

        return "\n".join(lines)


def _format_confidence(confidence: float | None) -> str:
    if confidence is None:
        return "ERROR"
    return f"{confidence:.2f}"


def _format_agent_votes(agent_votes: dict[str, float]) -> str:
    if not agent_votes:
        return "-"
    return ", ".join(f"{name}:{confidence:.1f}" for name, confidence in agent_votes.items())


def _format_round2(did_round2: bool, status: str) -> str:
    if status == "error" and not did_round2:
        return "-"
    return "yes" if did_round2 else "no"
