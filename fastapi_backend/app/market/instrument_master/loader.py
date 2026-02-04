import csv
from pathlib import Path

MASTER_PATH = Path(__file__).parent / "api-scrip-master-detailed.csv"

class InstrumentMaster:
    def __init__(self):
        self.rows = []

    def load(self):
        with open(MASTER_PATH, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.rows = list(reader)

        print(f"[OK] Instrument master loaded: {len(self.rows)} records")

MASTER = InstrumentMaster()
