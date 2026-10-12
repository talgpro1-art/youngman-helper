"""Offline Streamlit smoke tests for the published TOP50 data and entrant cards."""
from pathlib import Path
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
        table = self.app.dataframe[0].value
        self.assertEqual(len(table), 50)
        self.assertEqual(table['순위'].tolist(), list(range(1, 51)))
        self.assertEqual(set(table['기준월']), {'국산 2026-09', '수입 2026-09'})
        self.assertEqual(table.iloc[-1]['차량'], '기아 EV4')
        captions = '\n'.join(item.value for item in self.app.caption)
        self.assertNotIn('국산·수입 기준월이 다른', captions)
        self.assertIn('이전 앱 반영 순위 대비', captions)
        markdown = '\n'.join(item.value for item in self.app.markdown)
        for name, rank in [('벤츠 The New S-Class', 34), ('폴스타 Polestar 4', 43), ('BMW 3 Series', 47)]:
            row = table.loc[table['차량'].eq(name)].iloc[0]
            self.assertEqual((row['순위'], row['이전 대비']), (rank, 'NEW'))
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
            self.assertEqual(len(self.app.expander), 1)
            expected = master.loc[master.model.eq(model)].iloc[0]
            markdown = '\n'.join(item.value for item in self.app.markdown)
            self.assertIn(expected.price_url.replace('&', '&amp;'), markdown)
            self.assertIn(expected.image_url.replace('&', '&amp;'), markdown)
            self.app.text_input[0].set_value('')
            self.app.text_input[1].set_value('')
            self.run_app()
            self.assertIn('표시 차량: 50개', [item.value for item in self.app.caption])
            self.assertEqual(len(self.app.expander), 50)

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
