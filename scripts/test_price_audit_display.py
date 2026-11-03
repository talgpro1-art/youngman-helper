"""Historical price checks apply only to the exact vehicle and current URL."""
import ast
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def price_helpers(status_path):
    tree = ast.parse((ROOT / 'app.py').read_text())
    names = {'safe_str', 'load_price_checks', 'price_verification_label'}
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    for node in functions:
        node.decorator_list = []
    scope = {'pd': pd, 'LINK_STATUS': status_path}
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'app.py', 'exec'), scope)
    return scope


class PriceAuditDisplayTests(unittest.TestCase):
    def test_latest_check_is_selected_per_vehicle_and_exact_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'status.csv'
            pd.DataFrame([
                dict(vehicle='차량 A', url='https://official/current.pdf', doc_type='가격표', checked_at='2026-10-01', verification_status='MATCHED', rank=99),
                dict(vehicle='차량 A', url='https://official/current.pdf', doc_type='가격표', checked_at='2026-10-02', verification_status='ERROR', rank=98),
                dict(vehicle='차량 A', url='https://official/old.pdf', doc_type='가격표', checked_at='2026-11-03', verification_status='MATCHED', rank=97),
                dict(vehicle='차량 B', url='https://official/current.pdf', doc_type='가격표', checked_at='2026-11-01', verification_status='OFFICIAL_PAGE', rank=96),
                dict(vehicle='차량 A', url='https://official/current.pdf', doc_type='추가PDF', checked_at='2026-11-04', verification_status='MATCHED', rank=95),
            ]).to_csv(path, index=False)
            checks = price_helpers(path)['load_price_checks'](0)
            self.assertEqual(len(checks), 3)
            current = checks[(checks.vehicle == '차량 A') & (checks.url == 'https://official/current.pdf')].iloc[0]
            self.assertEqual(current.verification_status, 'ERROR')
            self.assertEqual(current.checked_at, '2026-10-02')
            self.assertNotIn('rank', checks.columns)

    def test_missing_url_never_invents_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'status.csv'
            helpers = price_helpers(path)
            self.assertIn('url', helpers['load_price_checks'](0).columns)
            pd.DataFrame([dict(vehicle='차량 A', doc_type='가격표', verification_status='MATCHED', checked_at='2026-11-03')]).to_csv(path, index=False)
            self.assertEqual(helpers['load_price_checks'](1).url.tolist(), [''])

    def test_model_text_match_does_not_claim_generation_or_year_verification(self):
        label = price_helpers(Path('/nonexistent'))['price_verification_label']
        self.assertEqual(label('MATCHED'), '차종명 일치 · 세대/연식 미검증')
        self.assertEqual(label(''), '검수 대기')
        self.assertEqual(label('OFFICIAL_PAGE'), '공식 페이지')

    def test_rendered_badges_do_not_follow_another_url_or_vehicle(self):
        master = pd.read_csv(ROOT / 'vehicle_master.csv', dtype=str).fillna('')
        first, second, third = [master.iloc[i] for i in range(3)]
        checks = pd.DataFrame([
            dict(vehicle=first.vehicle, url='https://official/old.pdf', doc_type='가격표', checked_at='2026-11-03', verification_status='MATCHED', verification_detail='Historical other URL', rank=500),
            dict(vehicle=second.vehicle, url=second.price_url, doc_type='가격표', checked_at='2026-10-02', verification_status='MATCHED', verification_detail='Exact current URL', rank=501),
            dict(vehicle=second.vehicle, url='https://official/another.pdf', doc_type='가격표', checked_at='2026-11-03', verification_status='ERROR', verification_detail='Newer other URL', rank=502),
            dict(vehicle='다른 차량', url=third.price_url, doc_type='가격표', checked_at='2026-11-03', verification_status='MATCHED', verification_detail='Same URL other vehicle', rank=503),
        ])
        original = pd.read_csv

        def local_csv(source, *args, **kwargs):
            if str(source) == str(ROOT / 'data/link_status.csv'):
                return checks.copy()
            if isinstance(source, str) and source.startswith(('http://', 'https://')):
                raise OSError('Offline app test')
            return original(source, *args, **kwargs)

        with patch.object(pd, 'read_csv', side_effect=local_csv):
            app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        self.assertFalse(app.exception)
        cards = [item.value for item in app.markdown if '<article class="vehicle-card"' in item.value]
        self.assertEqual(len(cards), 50)
        self.assertIn('가격표 검수: 검수 대기', cards[0])
        self.assertNotIn('2026-11-03', cards[0])
        self.assertIn('가격표 검수: 차종명 일치 · 세대/연식 미검증 · 2026-10-02', cards[1])
        self.assertNotIn('2026-11-03', cards[1])
        self.assertIn('가격표 검수: 검수 대기', cards[2])
        for card, (_, row) in zip(cards, master.iterrows()):
            self.assertIn(f'aria-label="{row["rank"]}위 {row.vehicle}"', card)
        price_expanders = [e for e in app.expander if '위 · ' in e.label]
        self.assertEqual(len(price_expanders), 50)
        self.assertIn('가격표 검수: 검수 대기', [c.value for c in price_expanders[0].caption])
        self.assertIn('가격표 검수: 차종명 일치 · 세대/연식 미검증 · 2026-10-02', [c.value for c in price_expanders[1].caption])


if __name__ == '__main__':
    unittest.main()
