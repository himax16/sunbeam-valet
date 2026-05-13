from sunbeam_valet.formatters.base import OutputFormatter
from sunbeam_valet.formatters.markdown import MarkdownFormatter

FORMATTERS: dict[str, type[OutputFormatter]] = {
    "markdown": MarkdownFormatter,
}


def get_formatter(name: str) -> OutputFormatter:
    if name not in FORMATTERS:
        raise ValueError(f"Unknown formatter: {name}. Available: {list(FORMATTERS.keys())}")
    return FORMATTERS[name]()
