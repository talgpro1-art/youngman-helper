"""Offline regression checks for the reviewed monthly update."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shutil
import json
import ast
import pandas as pd
import build_combined_sales_rankings as build
import check_price_links as checker


class SalesRefreshTests(unittest.TestCase):
    def test_snapshot_and_metadata(self):
        master = pd.read_csv(build.VEHICLE_MASTER, dtype=str).fillna("")
        sales = pd.read_csv(build.MONTHLY_SALES)
        reviewed = pd.read_csv(build.REVIEWED_SALES)
        self.assertEqual(len(master), 50)
        self.assertEqual(len(reviewed), 79)
        self.assertFalse(reviewed.duplicated(["brand", "model"]).any())
        expected = reviewed.sort_values("units_sold", ascending=False, kind="stable").head(50)
        self.assertEqual(list(sales.model), list(expected.model))
        self.assertEqual(list(sales.units_sold), list(expected.units_sold))
        self.assertEqual(list(master['rank'].astype(int)), list(range(1, 51)))
        self.assertEqual(master.source_period.value_counts().to_dict(), {"국산 2026-09": 40, "수입 2026-08": 10})
        self.assertTrue(master.price_url.str.startswith("https://").all())
        old = pd.read_csv(build.BASELINE, dtype=str).fillna("").set_index(["brand", "model"])
        overrides = {build.row_key(item['brand'], item['model']): item for item in json.loads(build.VEHICLE_UPDATES.read_text(encoding='utf-8'))}
        for _, row in master.iterrows():
            key = (row.brand, row.model)
            old_rank = int(old.loc[key, 'rank']) if key in old.index else None
            self.assertEqual(row.rank_change, build.rank_change(old_rank, int(row['rank'])))
            if key in old.index:
                for col in ['image_url', 'image_file', 'image_source_url', 'image_review_status']:
                    if old.loc[key, col]:
                        expected_value = overrides.get(build.row_key(*key), {}).get(col, old.loc[key, col])
                        self.assertEqual(row[col], expected_value, (key, col))
        self.assertNotIn('아반떼', master.model.tolist())
        self.assertIn('디 올 뉴 아반떼', master.model.tolist())
        self.assertIn('더 뉴 아이오닉 6', master.model.tolist())
        self.assertEqual(sales.iloc[-1].model, '캐스퍼 일렉트릭')
        self.assertEqual(int(sales.iloc[-1].units_sold), 478)
        self.assertEqual(int(reviewed.loc[reviewed.source_period == '국산 2026-09', 'units_sold'].sum()), 100083)
        self.assertEqual(int(reviewed.loc[reviewed.model == '3 Series', 'units_sold'].iloc[0]), 468)

    def test_repeat_run_is_stable_and_invalid_input_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / 'data' / 'sales_snapshot'
            snapshot.mkdir(parents=True)
            master = root / 'vehicle_master.csv'
            baseline = snapshot / 'baseline.csv'
            reviewed = snapshot / 'reviewed_sales.csv'
            for src, dest in [(build.VEHICLE_MASTER, master), (build.BASELINE, baseline), (build.REVIEWED_SALES, reviewed), (build.VEHICLE_UPDATES, snapshot / build.VEHICLE_UPDATES.name)]:
                shutil.copy2(src, dest)
            before = master.read_text(encoding="utf-8-sig")
            with patch.multiple(build, ROOT=root, VEHICLE_MASTER=master, MONTHLY_SALES=snapshot / 'monthly_sales.csv', BASELINE=baseline, REVIEWED_SALES=reviewed, VEHICLE_UPDATES=snapshot / build.VEHICLE_UPDATES.name):
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

    def test_selected_images_have_model_review_evidence(self):
        master = pd.read_csv(build.VEHICLE_MASTER, dtype=str).fillna('')
        audit = json.loads((build.MONTHLY_SALES.parent / 'image_review_2026-10-02.json').read_text())
        evidence = {(row['brand'], row['model']): row for row in audit['records']}
        self.assertEqual(set(evidence), set(zip(master.brand, master.model)))
        self.assertEqual(audit['totals']['selected_images_bytes_decoded_and_visually_reviewed'], 50)
        for _, row in master.iterrows():
            item = evidence[(row.brand, row.model)]
            self.assertEqual(row.image_review_status, 'approved')
            self.assertIn(row.image_source_type, {'official_site', 'official_newsroom', 'official_press_release'})
            self.assertEqual(row.image_url, item['image_url'])
            self.assertEqual(row.image_source_url, item['source_url'])
            self.assertEqual(len(item['sha256']), 64)
            self.assertGreater(item['width'], 0)
            self.assertGreater(item['height'], 0)
        truck = master.loc[master.model.eq('버스/트럭')].iloc[0]
        self.assertIn('대표 이미지', truck.note)

    def test_document_button_labels_preserve_price_catalog_distinction(self):
        # Load just the pure link helpers without running Streamlit's module-level UI.
        tree = ast.parse((build.ROOT / 'app.py').read_text())
        names = {'safe_str', 'is_pdf_url', 'is_hybrid_price_url', 'price_button_label', 'price_links'}
        module = ast.Module(body=[node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
        scope = {'pd': pd}
        exec(compile(module, 'app.py', 'exec'), scope)
        links = scope['price_links'](pd.Series({'price_url': 'https://example.com/model-price.pdf', 'catalog_url': 'https://example.com/model-catalog.pdf'}))
        self.assertEqual([item[1] for item in links], ['공식 가격표', '공식 카탈로그'])
        links = scope['price_links'](pd.Series({'price_url': 'https://example.com/model-price.pdf', 'catalog_url': 'https://example.com/model-hev-price.pdf'}))
        self.assertEqual([item[1] for item in links], ['공식 가격표(일반)', '공식 가격표(하이브리드)'])
        links = scope['price_links'](pd.Series({'price_url': 'https://example.com/price_pv5-cargo.pdf', 'catalog_url': 'https://example.com/price_pv5-passenger.pdf'}))
        self.assertEqual([item[1] for item in links], ['공식 가격표(카고)', '공식 가격표(패신저)'])
        links = scope['price_links'](pd.Series({'price_url': 'https://example.com/price.pdf', 'catalog_url': 'https://example.com/model/overview.html'}))
        self.assertEqual(links[1][1], '공식 모델 안내')

    def test_checker_does_not_claim_unchecked_success(self):
        self.assertEqual(checker.browser_only_status('https://www.tesla.com/ko_kr/modely')['status_code'], 'BROWSER_REQUIRED')
        self.assertIsNone(checker.browser_only_status('https://www.bmw.co.kr/price.pdf'))
        checker.fetch_hash.cache_clear()
        with patch.object(checker.requests, 'get') as get:
            get.return_value.ok = True
            get.return_value.content = b'<html>error</html>'
            with self.assertRaises(ValueError):
                checker.fetch_hash('https://example.com/price.pdf')

    def test_pdf_model_name_verification(self):
        matched = checker.semantic_verification(
            '쏘렌토',
            'https://example.com/price.pdf',
            {'status_code': 200, '_pdf_text': 'The 2027 KIA SORENTO 가격표'},
        )
        self.assertEqual(matched[0], 'MATCHED')
        for model, text in [('더 뉴 아이오닉 6', 'The new IONIQ 6 PRICE'), ('캐스퍼 일렉트릭', 'CASPER ELECTRIC PRICE'), ('GLC-Class', 'Mercedes-Benz GLC 300 4MATIC')]:
            self.assertEqual(checker.semantic_verification(model, 'https://example.com/price.pdf', {'status_code': 200, '_pdf_text': text})[0], 'MATCHED')
        mismatch = checker.semantic_verification(
            '쏘렌토',
            'https://example.com/price.pdf',
            {'status_code': 200, '_pdf_text': 'KIA CARNIVAL PRICE LIST'},
        )
        self.assertEqual(mismatch[0], 'MISMATCH')
        degraded = checker.semantic_verification(
            'SEALION 7',
            'https://example.com/catalog.pdf',
            {'status_code': 200, '_pdf_text': 'BYD SEALION \ufffd SPECIFICATIONS'},
        )
        self.assertEqual(degraded[0], 'TEXT_UNAVAILABLE')
        official_page = checker.semantic_verification(
            'G80',
            'https://www.genesis.com/price-list',
            {'status_code': 200},
        )
        self.assertEqual(official_page[0], 'OFFICIAL_PAGE')


if __name__ == '__main__':
    unittest.main()
