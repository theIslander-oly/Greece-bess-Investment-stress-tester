"""Whole-second receipts must survive CSV beside fractional-second receipts."""

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from greek_bess.data.point_in_time import read_point_in_time_csv


class ReceiptPrecisionTests(unittest.TestCase):
    def test_mixed_iso_precision_preserves_every_receipt_in_either_order(self) -> None:
        receipts = ["2026-09-11 16:16:02.952663+00:00", "2026-09-11 16:16:03+00:00"]
        for order in (receipts, receipts[::-1]):
            with self.subTest(first=order[0]), tempfile.TemporaryDirectory() as directory:
                rows = []
                for hour, receipt in enumerate(order):
                    start = pd.Timestamp("2026-08-20T00:00:00Z") + pd.Timedelta(hour, unit="h")
                    rows.append({
                        "delivery_start_utc": start,
                        "delivery_end_utc": start + pd.Timedelta(1, unit="h"),
                        "market_day": "2026-08-20", "source": "noaa_gfs",
                        "dataset": "gfs.0p25", "variable": "temperature_2m", "area": "GR",
                        "unit": "K", "resolution_minutes": 60, "value": 300.0,
                        "published_at_utc": "2026-08-19T04:00:00Z",
                        "retrieved_at_utc": receipt, "source_document_id": f"synthetic-{hour}",
                        "source_revision": "1", "raw_sha256": "a" * 64,
                        "forecast_issue_time_utc": "2026-08-19T00:00:00Z",
                        "forecast_horizon_minutes": 1440 + hour * 60,
                        "availability_evidence_grade": "provider_declared",
                        "availability_evidence_detail": "Synthetic receipt precision regression",
                    })
                path = Path(directory) / "features.csv"
                pd.DataFrame(rows).to_csv(path, index=False)
                restored = read_point_in_time_csv(path)
                self.assertEqual(list(restored["retrieved_at_utc"]),
                                 [pd.Timestamp(value) for value in order])


if __name__ == "__main__":
    unittest.main()
