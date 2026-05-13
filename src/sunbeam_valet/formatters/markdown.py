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
                f"| {row.confidence} "
                f"| {row.agent_votes} "
                f"| {row.status} "
                f"| {row.round2} |"
            )

        if round2_count > 0:
            lines.append("")
            lines.append(f"_Round 2 triggered: {round2_count}/{len(rows)} bugs_")

        return "\n".join(lines)
