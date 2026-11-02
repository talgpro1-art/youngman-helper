"""Offline Streamlit smoke tests for the published TOP50 data and entrant cards."""
from pathlib import Path
import json
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppSalesTests(unittest.TestCase):
    def setUp(self):
        original_read_csv = pd.read_csv

        def local_read_csv(source, *args, **kwargs):
            # Exercise the application's existing local-roadmap fallback; keep QA offline.
            if isinstance(source, str) and source.startswith(('http://', 'https://')):
                raise OSError('Offline smoke test')
            return original_read_csv(source, *args, **kwargs)

        self.reader = patch.object(pd, 'read_csv', side_effect=local_read_csv)
        self.reader.start()
        self.addCleanup(self.reader.stop)
        self.app = AppTest.from_file(str(ROOT / 'app.py'), default_timeout=20).run()
        self.assertFalse(self.app.exception)

    def run_app(self):
        self.app.run()
        self.assertFalse(self.app.exception)

    def test_complete_table_periods_and_entrant_cards(self):
        master = pd.read_csv(ROOT / 'vehicle_master.csv').fillna('')
        cards = [item.value for item in self.app.markdown if '<article class="vehicle-card"' in item.value]
        self.assertEqual(len(cards), 50)
        self.assertEqual(master['rank'].tolist(), list(range(1, 51)))
        self.assertEqual(set(master.source_period), {'국산 2026-09', '수입 2026-09'})
        for card, (_, row) in zip(cards, master.iterrows()):
            self.assertIn(f'aria-label="{row["rank"]}위 {row.vehicle}"', card)
            self.assertIn(row.source_period, card)
            self.assertIn(str(row.units_sold), card)
        self.assertIn('기아 EV4', cards[-1])
        captions = '\n'.join(item.value for item in self.app.caption)
        self.assertNotIn('국산·수입 기준월이 다른', captions)
        self.assertIn('이전 앱 반영 순위 대비', captions)
        markdown = '\n'.join(item.value for item in self.app.markdown)
        for name, rank in [('벤츠 The New S-Class', 34), ('폴스타 Polestar 4', 43), ('BMW 3 Series', 47)]:
            row = master.loc[master.vehicle.eq(name)].iloc[0]
            self.assertEqual((row['rank'], row['rank_change']), (rank, 'NEW'))
            self.assertIn(name, markdown)
        self.assertIn('11,421', markdown)
        self.assertIn('2,748', markdown)

    def test_search_price_links_and_repeated_reset(self):
        master = pd.read_csv(ROOT / 'vehicle_master.csv').fillna('')
        for model in ['The New S-Class', 'Polestar 4', '3 Series']:
            self.app.text_input[0].set_value(model)
            self.app.text_input[1].set_value(model)
            self.run_app()
            self.assertIn('표시 차량: 1개', [item.value for item in self.app.caption])
            self.assertEqual(len(self.app.expander), 2)
            expected = master.loc[master.model.eq(model)].iloc[0]
            markdown = '\n'.join(item.value for item in self.app.markdown)
            self.assertIn(expected.price_url.replace('&', '&amp;'), markdown)
            self.assertIn(expected.image_url.replace('&', '&amp;'), markdown)
            self.app.text_input[0].set_value('')
            self.app.text_input[1].set_value('')
            self.run_app()
            self.assertIn('표시 차량: 50개', [item.value for item in self.app.caption])
            self.assertEqual(len(self.app.expander), 51)

    def test_literal_search_no_matches_and_segment_reset(self):
        for query in ['[', '없는차량xyz']:
            self.app.text_input[0].set_value(query)
            self.app.text_input[1].set_value(query)
            self.run_app()
            self.assertIn('표시 차량: 0개', [item.value for item in self.app.caption])
            self.assertTrue(any('검색 결과가 없습니다' in item.value for item in self.app.info))
        self.app.text_input[0].set_value('')
        self.app.text_input[1].set_value('')
        self.app.selectbox[0].select('SUV')
        self.run_app()
        master = pd.read_csv(ROOT / 'vehicle_master.csv')
        expected = master[master.segment.eq('SUV')]
        cards = [item.value for item in self.app.markdown if '<article class="vehicle-card"' in item.value]
        self.assertEqual(len(cards), len(expected))
        self.app.selectbox[0].select('전체')
        self.run_app()
        self.assertIn('표시 차량: 50개', [item.value for item in self.app.caption])

    def test_editorial_previews_copy_and_navigation(self):
        markdown = '\n'.join(item.value for item in self.app.markdown)
        self.assertIn('<h1>영맨헬퍼</h1>', markdown)
        self.assertIn('차량 판매순위부터 가격표까지 원클릭으로', markdown)
        self.assertNotIn('보안 원칙: 고객 개인정보, 실제 계약정보', '\n'.join(item.value for item in self.app.caption))
        self.assertEqual([tab.label for tab in self.app.tabs], ['TOP50', '가격표', '옵션', '업무효과'])
        preview = next(item.value for item in self.app.markdown if 'class="updates-preview"' in item.value)
        notifications = json.loads((ROOT / 'data/notifications.json').read_text())[:5]
        selected = next(item for item in notifications if item.get('source') == 'price_link_checker')
        self.assertIn(selected['title'], preview)
        self.assertIn(selected['date'], preview)
        self.assertIn('data-preview="roadmap"', preview)
        self.assertIn('소식 전체보기', self.app.expander[0].label)

    def test_new_entrant_options_have_safe_empty_state(self):
        self.app.radio[0].set_value('전체 차량')
        self.run_app()
        for name in ['벤츠 The New S-Class', '폴스타 Polestar 4', 'BMW 3 Series']:
            self.app.selectbox[1].select(name)
            self.run_app()
            self.assertIn('아직 옵션 설명 데이터가 없습니다.', [item.value for item in self.app.info])
        self.app.radio[0].set_value('TOP10 데모')
        self.run_app()
        self.assertEqual(len(self.app.selectbox[1].options), 10)


if __name__ == '__main__':
    unittest.main()
