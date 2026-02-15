"""Export scan results to CSV or JSON."""

import csv
import json

from .models import ScanResult
from .scorer import classify_sender


def export_scan(scan_result: ScanResult, format: str, output_path: str) -> None:
    """Export scan results to a file.

    Args:
        scan_result: The scan result to export.
        format: Output format, either 'csv' or 'json'.
        output_path: Path to write the output file.
    """
    from .constants import SCORE_UNCERTAIN

    _CLASS_ORDER = {"newsletter": 0, "likely_newsletter": 1, "uncertain": 2}
    senders_sorted = sorted(
        [s for s in scan_result.senders.values() if s.score >= SCORE_UNCERTAIN],
        key=lambda s: (_CLASS_ORDER.get(classify_sender(s.score), 3), -s.message_count),
    )

    if format == "csv":
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "email",
                    "name",
                    "message_count",
                    "score",
                    "classification",
                    "sample_subjects",
                ],
            )
            writer.writeheader()
            for sender in senders_sorted:
                writer.writerow(
                    {
                        "email": sender.email,
                        "name": sender.name,
                        "message_count": sender.message_count,
                        "score": sender.score,
                        "classification": classify_sender(sender.score),
                        "sample_subjects": "; ".join(sender.sample_subjects),
                    }
                )
    elif format == "json":
        rows = []
        for sender in senders_sorted:
            rows.append(
                {
                    "email": sender.email,
                    "name": sender.name,
                    "message_count": sender.message_count,
                    "score": sender.score,
                    "classification": classify_sender(sender.score),
                    "sample_subjects": sender.sample_subjects,
                }
            )
        with open(output_path, "w") as f:
            json.dump(rows, f, indent=2)

    print(f"Results saved to {output_path}")
