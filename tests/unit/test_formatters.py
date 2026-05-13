from sunbeam_valet.formatters.markdown import MarkdownFormatter
from sunbeam_valet.models import TableRow


class TestMarkdownFormatter:
    def test_format_empty_rows(self):
        formatter = MarkdownFormatter()
        result = formatter.format([], 0)
        assert "Bug Triage Report" in result
        assert "|" in result

    def test_format_single_row(self):
        formatter = MarkdownFormatter()
        rows = [
            TableRow(
                bug_reference="LP:#12345",
                bug_reference_url="https://bugs.launchpad.net/bugs/12345",
                summary="Test bug summary",
                confidence="0.85",
                agent_votes="sec:0.9, tri:0.6",
                status="ok",
                round2="no",
            )
        ]
        result = formatter.format(rows, 0)
        assert "LP:#12345" in result
        assert "0.85" in result
        assert "ok" in result

    def test_format_with_round2(self):
        formatter = MarkdownFormatter()
        rows = [
            TableRow(
                bug_reference="LP:#12345",
                bug_reference_url="https://bugs.launchpad.net/bugs/12345",
                summary="Test",
                confidence="0.72",
                agent_votes="sec:0.9",
                status="round2",
                round2="yes",
            )
        ]
        result = formatter.format(rows, 1)
        assert "Round 2 triggered: 1/1 bugs" in result

    def test_format_error_row(self):
        formatter = MarkdownFormatter()
        rows = [
            TableRow(
                bug_reference="LP:#99999",
                bug_reference_url="https://bugs.launchpad.net/bugs/99999",
                summary="Connection timeout",
                confidence="ERROR",
                agent_votes="-",
                status="error",
                round2="-",
            )
        ]
        result = formatter.format(rows, 0)
        assert "ERROR" in result
        assert "error" in result
