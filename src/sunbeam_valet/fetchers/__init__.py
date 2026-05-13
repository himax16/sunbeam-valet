from sunbeam_valet.fetchers.base import BugFetcher
from sunbeam_valet.fetchers.watchtower import WatchtowerFetcher

FETCHERS: dict[str, type[BugFetcher]] = {
    "watchtower": WatchtowerFetcher,
}


def get_fetcher(name: str, config) -> BugFetcher:
    if name not in FETCHERS:
        raise ValueError(f"Unknown fetcher: {name}. Available: {list(FETCHERS.keys())}")
    return FETCHERS[name](config)
