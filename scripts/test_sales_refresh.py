"""Offline regression checks for the reviewed monthly update."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shutil
import pandas as pd
import build_combined_sales_rankings as build
import check_price_links as checker


class SalesRefreshTests(unittest.TestCase):
    def test_snapshot_and_metadata(self):
        master = pd.read_csv(build.VEHICLE_MASTER, dtype=str).fillna("")
        sales = pd.read_csv(build.MONTHLY_SALES)
        reviewed = pd.read_csv(build.REVIEWED_SALES)
        self.assertEqual(len(master), 50)
        self.assertEqual(len(reviewed), 78)
        self.assertFalse(reviewed.duplicated(["brand", "model"]).any())
        expected = reviewed.sort_values("units_sold", ascending=False, kind="stable").head(50)
        self.assertEqual(list(sales.model), list(expected.model))
        self.assertEqual(list(sales.units_sold), list(expected.units_sold))
        self.assertEqual(list(master['rank'].astype(int)), list(range(1, 51)))
        self.assertEqual(master.source_period.value_counts().to_dict(), {"국산 2026-08": 40, "수입 2026-08": 10})
        self.assertTrue(master.price_url.str.startswith("https://").all())
        old = pd.read_csv(build.BASELINE, dtype=str).fillna("").set_index(["brand", "model"])
        for _, row in master.iterrows():
            key = (row.brand, row.model)
            old_rank = int(old.loc[key, 'rank']) if key in old.index else None
            self.assertEqual(row.rank_change, build.rank_change(old_rank, int(row['rank'])))
            if key in old.index:
                for col in ['image_url', 'image_file', 'image_source_url', 'image_review_status']:
                    if old.loc[key, col]:
                        self.assertEqual(row[col], old.loc[key, col], (key, col))
        avante = master.set_index('model')
        self.assertNotEqual(avante.loc['아반떼', 'price_url'], avante.loc['디 올 뉴 아반떼', 'price_url'])
        self.assertEqual(int(sales.iloc[-1].units_sold), 481)
        self.assertEqual(int(reviewed.loc[reviewed.model == '3 Series', 'units_sold'].iloc[0]), 468)

    def test_repeat_run_is_stable_and_invalid_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / 'data' / 'sales_snapshot'
            snapshot.mkdir(parents=True)
            master = root / 'vehicle_master.csv'
            baseline = snapshot / 'baseline.csv'
            reviewed = snapshot / 'reviewed_sales.csv'
            for src, dest in [(build.VEHICLE_MASTER, master), (build.BASELINE, baseline), (build.REVIEWED_SALES, reviewed), (build.MONTHLY_SALES.parent / 'price_updates_2026-09-07.json', snapshot / 'price_updates_2026-09-07.json')]:
                shutil.copy2(src, dest)
            before = master.read_text(encoding="utf-8-sig")
            with patch.multiple(build, ROOT=root, VEHICLE_MASTER=master, MONTHLY_SALES=snapshot / 'monthly_sales.csv', BASELINE=baseline, REVIEWED_SALES=reviewed):
                build.main()
                self.assertEqual(before, master.read_text(encoding="utf-8-sig"))
                build.main()
                self.assertEqual(before, master.read_text(encoding="utf-8-sig"))
                data = pd.read_csv(reviewed)
                pd.concat([data, data.iloc[:1]]).to_csv(reviewed, index=False)
                with self.assertRaises(ValueError):
                    build.main()
                self.assertEqual(before, master.read_text(encoding="utf-8-sig"))
                data.loc[0, 'units_sold'] = -1
                data.to_csv(reviewed, index=False)
                with self.assertRaises(ValueError):
                    build.main()
                data.loc[0, 'units_sold'] = 1
                data.loc[0, 'source_period'] = '국산 2026-99'
                data.to_csv(reviewed, index=False)
                with self.assertRaises(ValueError):
                    build.main()

    def test_checker_does_not_claim_unchecked_success(self):
        self.assertEqual(checker.browser_only_status('https://www.tesla.com/ko_kr/modely')['status_code'], 'BROWSER_REQUIRED')
        self.assertIsNone(checker.browser_only_status('https://www.bmw.co.kr/price.pdf'))
        checker.fetch_hash.cache_clear()
        with patch.object(checker.requests, 'get') as get:
            get.return_value.ok = True
            get.return_value.content = b'<html>error</html>'
            with self.assertRaises(ValueError):
                checker.fetch_hash('https://example.com/price.pdf')


if __name__ == '__main__':
    unittest.main()
