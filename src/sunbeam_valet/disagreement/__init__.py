from sunbeam_valet.disagreement.base import DisagreementMetric
from sunbeam_valet.disagreement.std_dev import StdDevDisagreementMetric

METRICS: dict[str, type[DisagreementMetric]] = {
    "std_dev": StdDevDisagreementMetric,
}


def get_metric(name: str) -> DisagreementMetric:
    if name not in METRICS:
        raise ValueError(f"Unknown disagreement metric: {name}. Available: {list(METRICS.keys())}")
    return METRICS[name]()
