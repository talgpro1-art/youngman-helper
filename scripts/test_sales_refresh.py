"""Offline regression checks for the reviewed monthly update."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import shutil
import json
import ast
import hashlib
from contextlib import contextmanager
import pandas as pd
import build_combined_sales_rankings as build
import check_price_links as checker


class SalesRefreshTests(unittest.TestCase):
    def test_snapshot_and_metadata(self):
        master = pd.read_csv(build.VEHICLE_MASTER, dtype=str).fillna("")
        sales = pd.read_csv(build.MONTHLY_SALES)
        reviewed = pd.read_csv(build.REVIEWED_SALES)
        self.assertEqual(len(master), 50)
        self.assertEqual(len(reviewed), 80)
        self.assertFalse(reviewed.duplicated(["brand", "model"]).any())
        expected = reviewed.sort_values("units_sold", ascending=False, kind="stable").head(50)
        self.assertEqual(list(sales.model), list(expected.model))
        self.assertEqual(list(sales.units_sold), list(expected.units_sold))
        self.assertEqual(list(master['rank'].astype(int)), list(range(1, 51)))
        self.assertEqual(master.source_period.value_counts().to_dict(), {"국산 2026-09": 39, "수입 2026-09": 11})
        self.assertTrue(master.price_url.str.startswith("https://").all())
        old = pd.read_csv(build.BASELINE, dtype=str).fillna("").set_index(["brand", "model"], drop=False)
        for _, row in master.iterrows():
            key = (row.brand, row.model)
            old_rank = int(old.loc[key, 'rank']) if key in old.index else None
            self.assertEqual(row.rank_change, build.rank_change(old_rank, int(row['rank'])))
            if key in old.index:
                for col in set(build.COLUMNS) - {'rank', 'rank_change', 'units_sold', 'source_period'}:
                    self.assertEqual(row[col], old.loc[key, col], (key, col))
        self.assertNotIn('아반떼', master.model.tolist())
        self.assertIn('디 올 뉴 아반떼', master.model.tolist())
        self.assertIn('더 뉴 아이오닉 6', master.model.tolist())
        self.assertEqual(sales.iloc[-1].model, 'EV4')
        self.assertEqual(int(sales.iloc[-1].units_sold), 498)
        self.assertEqual(int(reviewed.loc[reviewed.source_period == '국산 2026-09', 'units_sold'].sum()), 100083)
        self.assertEqual(int(reviewed.loc[reviewed.model == '3 Series', 'units_sold'].iloc[0]), 527)
        self.assertEqual(set(master.loc[master.rank_change.eq('NEW'), 'model']), {'The New S-Class', 'Polestar 4', '3 Series'})
        self.assertFalse(set(master.model) & {'GLC-Class', 'SEALION 6 DM-i', '캐스퍼 일렉트릭'})

    @contextmanager
    def isolated_build(self, first_run=False):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / 'data' / 'sales_snapshot'
            snapshot.mkdir(parents=True)
            paths = dict(ROOT=root, VEHICLE_MASTER=root / 'vehicle_master.csv', MONTHLY_SALES=snapshot / 'monthly_sales.csv', BASELINE=snapshot / 'baseline.csv', REVIEWED_SALES=snapshot / 'reviewed_sales.csv', VEHICLE_UPDATES=snapshot / build.VEHICLE_UPDATES.name)
            for name in ['VEHICLE_MASTER', 'MONTHLY_SALES', 'BASELINE', 'REVIEWED_SALES', 'VEHICLE_UPDATES']:
                shutil.copy2(getattr(build, name), paths[name])
            if first_run:
                shutil.copy2(paths['BASELINE'], paths['VEHICLE_MASTER'])
                paths['BASELINE'].unlink()
            with patch.multiple(build, **paths):
                yield paths

    def test_repeat_run_preserves_bytes_timestamps_and_movement(self):
        with self.isolated_build():
            paths = [build.VEHICLE_MASTER, build.MONTHLY_SALES, build.BASELINE]
            before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths}
            build.main()
            build.main()
            self.assertEqual(before, {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in paths})

    def test_first_run_captures_actual_deployed_ranks_once(self):
        expected_master = build.VEHICLE_MASTER.read_bytes()
        expected_sales = build.MONTHLY_SALES.read_bytes()
        with self.isolated_build(first_run=True):
            original = build.VEHICLE_MASTER.read_bytes()
            build.main()
            self.assertEqual(build.BASELINE.read_bytes(), original)
            self.assertEqual(build.VEHICLE_MASTER.read_bytes(), expected_master)
            self.assertEqual(build.MONTHLY_SALES.read_bytes(), expected_sales)
            build.main()
            self.assertEqual(build.BASELINE.read_bytes(), original)
            self.assertEqual(build.VEHICLE_MASTER.read_bytes(), expected_master)

    def test_invalid_input_rejected_without_writes(self):
        with self.isolated_build(first_run=True):
            data = pd.read_csv(build.REVIEWED_SALES).fillna('')
            original = build.VEHICLE_MASTER.read_bytes()
            sales_before = build.MONTHLY_SALES.read_bytes()
            bad_inputs = [pd.concat([data, data.iloc[:1]])]
            for value in [-1, 0.5, float('inf'), '']:
                bad = data.astype({'units_sold': object}).copy()
                bad.loc[0, 'units_sold'] = value
                bad_inputs.append(bad)
            for value in ['국산 2026-99', '수입 2026-9', '2026-09']:
                bad = data.copy()
                bad.loc[0, 'source_period'] = value
                bad_inputs.append(bad)
            bad = data.copy()
            bad.loc[bad.model.eq('GLC-Class'), 'units_sold'] = 498
            bad_inputs.extend([bad, data.head(50)])
            for bad in bad_inputs:
                bad.to_csv(build.REVIEWED_SALES, index=False)
                with self.assertRaises(ValueError):
                    build.main()
                self.assertEqual(build.VEHICLE_MASTER.read_bytes(), original)
                self.assertEqual(build.MONTHLY_SALES.read_bytes(), sales_before)
                self.assertFalse(build.BASELINE.exists())

    def test_missing_entrant_metadata_is_blocked_before_writes(self):
        with self.isolated_build(first_run=True):
            before = build.VEHICLE_MASTER.read_bytes()
            build.VEHICLE_UPDATES.write_text('[]')
            with self.assertRaisesRegex(ValueError, 'Verified official metadata'):
                build.main()
            self.assertEqual(build.VEHICLE_MASTER.read_bytes(), before)
            self.assertFalse(build.BASELINE.exists())

    def test_retained_metadata_is_not_replaced_by_update_file(self):
        with self.isolated_build():
            before = build.VEHICLE_MASTER.read_bytes()
            overrides = json.loads(build.VEHICLE_UPDATES.read_text())
            overrides.append({'brand': '현대', 'model': '더 뉴 그랜저', 'price_url': 'https://example.com/stale.pdf', 'image_url': '', 'note': 'stale override'})
            build.VEHICLE_UPDATES.write_text(json.dumps(overrides))
            build.main()
            self.assertEqual(build.VEHICLE_MASTER.read_bytes(), before)

    def test_domestic_first_ties_and_mixed_periods(self):
        with self.isolated_build():
            data = pd.read_csv(build.REVIEWED_SALES)
            data.loc[data.model.eq('더 뉴 그랜저'), 'units_sold'] = 11421
            data.loc[data.source_period.str.startswith('수입'), 'source_period'] = '수입 2026-08'
            data.iloc[::-1].to_csv(build.REVIEWED_SALES, index=False)
            build.main()
            sales = pd.read_csv(build.MONTHLY_SALES)
            self.assertEqual(sales.model.iloc[:2].tolist(), ['더 뉴 그랜저', 'Model Y'])
            self.assertEqual(set(sales.source_period), {'국산 2026-09', '수입 2026-08'})

    def test_complete_source_reconciliation_and_generation_identity(self):
        raw = json.loads((build.MONTHLY_SALES.parent / 'source_rows_2026-10-12.json').read_text())
        reviewed = pd.read_csv(build.REVIEWED_SALES).fillna('')
        sales = pd.read_csv(build.MONTHLY_SALES)
        self.assertEqual(len(raw['domestic']), 67)
        self.assertEqual(len(raw['imports']), 155)
        self.assertEqual(sum(row['units'] for row in raw['domestic']), 100083)
        self.assertEqual(sum(row['units'] for row in raw['imports']), 34904)
        for market in ['domestic', 'imports']:
            rows = raw[market]
            self.assertEqual([row['rank'] for row in rows], list(range(1, len(rows) + 1)))
            self.assertTrue(all(type(row['units']) is int and row['units'] >= 0 for row in rows))
            self.assertEqual([row['units'] for row in rows], sorted([row['units'] for row in rows], reverse=True))
        imports = {row['source_url']: row for row in raw['imports']}
        self.assertEqual(len(imports), 155)
        for row in reviewed.itertuples():
            source = imports[row.source_model_url] if row.source_period.startswith('수입') else next(x for x in raw['domestic'] if x['model'] == row.model)
            self.assertEqual((row.model, row.units_sold, row.source_period), (source['model'], source['units'], source['market'] + ' ' + source['period']))
        complete = sorted(raw['domestic'] + raw['imports'], key=lambda row: -row['units'])
        self.assertEqual([(row.model, row.units_sold) for row in sales.itertuples()], [(row['model'], row['units']) for row in complete[:50]])
        self.assertEqual((complete[49]['model'], complete[49]['units'], complete[50]['model'], complete[50]['units']), ('EV4', 498, 'GLC-Class', 481))
        eclass = {row['source_url'].split('Model=')[-1]: row['units'] for row in raw['imports'] if row['model'] == 'E-Class'}
        self.assertEqual(eclass, {'4516': 2748, '3757': 1})
        self.assertEqual(sales.loc[sales.model.eq('E-Class'), 'units_sold'].tolist(), [2748])
        # This is the exact master blob deployed before this update, including old movements.
        baseline = build.BASELINE.read_bytes()
        self.assertEqual(hashlib.sha1(b'blob ' + str(len(baseline)).encode() + b'\0' + baseline).hexdigest(), '3e2047617d4ee47c47ba2893af5f81afdc1b1eea')

    def test_selected_images_have_model_review_evidence(self):
        master = pd.read_csv(build.VEHICLE_MASTER, dtype=str).fillna('')
        audit = json.loads((build.MONTHLY_SALES.parent / 'image_review_2026-10-02.json').read_text())
        evidence = {(row['brand'], row['model']): row for row in audit['records']}
        self.assertEqual(audit['totals']['selected_images_bytes_decoded_and_visually_reviewed'], 50)
        current = json.loads((build.MONTHLY_SALES.parent / 'image_review_2026-10-12.json').read_text())
        self.assertEqual(len(current['records']), 3)
        evidence.update({(row['brand'], row['model']): row for row in current['records']})
        self.assertEqual(len(set(zip(master.brand, master.model)) & set(evidence)), 50)
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
        self.assertFalse(scope['is_hybrid_price_url']('https://www.chevrolet.co.kr/chevrolet-price.pdf'))
        self.assertEqual(scope['price_button_label']('https://www.chevrolet.co.kr/chevrolet-price.pdf'), '공식 가격표')
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
