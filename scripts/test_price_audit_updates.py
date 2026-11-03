"""Audit coverage, exact guarded changes, and preservation of held/unrelated fields."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import pandas as pd

from apply_reviewed_price_updates import apply_updates, AUDIT, MASTER

BASELINE = AUDIT.parent / 'history/vehicle_master_before_2026-11-03-price-audit.csv'
URL_MODELS = {('현대', '쏘나타 디 엣지'), ('BMW', '5 Series'), ('BMW', 'X3'), ('르노', '그랑 콜레오스'), ('쉐보레', '트랙스 크로스오버')}
NOTE_MODELS = URL_MODELS | {('기아', '봉고 3'), ('기아', '레이 EV'), ('제네시스', 'G80'), ('제네시스', 'GV80'), ('제네시스', 'GV70')}


def frame(path):
    return pd.read_csv(path, dtype=str).fillna('').set_index(['brand', 'model'], drop=False)


class PriceAuditUpdateTests(unittest.TestCase):
    def test_exact_five_links_and_ten_notes_only(self):
        baseline = BASELINE.read_bytes()
        self.assertEqual(hashlib.sha1(b'blob ' + str(len(baseline)).encode() + b'\0' + baseline).hexdigest(), '9fe76232d25054bcebede776929da9e035136787')
        audit = json.loads(AUDIT.read_text())
        expected_scope = {(*key, 'price_url') for key in URL_MODELS} | {(*key, 'note') for key in NOTE_MODELS}
        self.assertEqual({(c['brand'], c['model'], c['field']) for c in audit['changes']}, expected_scope)
        self.assertEqual(len(audit['changes']), 15)
        before, after = frame(BASELINE), frame(MASTER)
        self.assertEqual(before.index.tolist(), after.index.tolist())
        self.assertEqual(before.columns.tolist(), after.columns.tolist())
        observed = set()
        for key in before.index:
            for col in before.columns:
                if before.loc[key, col] != after.loc[key, col]:
                    observed.add((*key, col))
        self.assertEqual(observed, expected_scope)
        for c in audit['changes']:
            key = (c['brand'], c['model'])
            self.assertEqual(before.loc[key, c['field']], c['old'])
            self.assertEqual(after.loc[key, c['field']], c['new'])

    def test_complete_coverage_and_held_links_unchanged(self):
        audit = json.loads(AUDIT.read_text())
        current = frame(MASTER)
        candidate = [r for r in audit['records'] if r['scope'] == 'candidate_top50']
        self.assertEqual(len(candidate), 50)
        self.assertEqual(len(audit['records']), 53)
        self.assertEqual({(r['brand'], r['model']) for r in candidate}, set(current.index))
        links = [l for r in candidate for l in r['links']]
        self.assertEqual(len(links), 90)
        self.assertEqual(sum(l['status'] == 'current' for l in links), 67)
        self.assertEqual(sum(l['status'] == 'outdated' for l in links), 12)
        self.assertEqual(sum(l['status'] == 'uncertain' for l in links), 11)
        self.assertEqual(sum(l['mutation'] == 'hold_content_verification' for l in links), 7)
        for r in candidate:
            key = (r['brand'], r['model'])
            for l in r['links']:
                self.assertTrue(l['checked_at'])
                self.assertTrue(l['evidence_urls'])
                if l['mutation'] != 'apply_verified_replacement':
                    self.assertEqual(current.loc[key, l['field']], l['existing_url'])
        bmw = next(r for r in audit['records'] if r['model'] == '3 Series')
        self.assertEqual(bmw['scope'], 'deployed_only_audit')
        self.assertEqual(next(l for l in bmw['links'] if l['field'] == 'catalog_url')['status'], 'current')

    def test_rebuild_is_exact_and_repeat_run_preserves_bytes_and_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'master.csv'
            shutil.copy2(BASELINE, path)
            apply_updates(path, AUDIT)
            self.assertEqual(path.read_bytes(), MASTER.read_bytes())
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            apply_updates(path, AUDIT)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_changed_precondition_rejects_all_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'master.csv'
            df = pd.read_csv(BASELINE, dtype=str).fillna('')
            df.loc[df.model.eq('쏘나타 디 엣지'), 'price_url'] = 'https://official.example/concurrent.pdf'
            df.to_csv(path, index=False, encoding='utf-8-sig')
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'Exact old value changed'):
                apply_updates(path, AUDIT)
            self.assertEqual(path.read_bytes(), before)

    def test_unverified_and_unrelated_mutations_are_rejected(self):
        audit = json.loads(AUDIT.read_text())
        held = next((r, l) for r in audit['records'] for l in r['links'] if l['mutation'] == 'hold_content_verification')
        r, link = held
        bad = copy.deepcopy(audit)
        bad['changes'].append(dict(brand=r['brand'], model=r['model'], field=link['field'], old=link['existing_url'], new=link['proposed_url'], evidence_urls=link['evidence_urls'], checked_at=link['checked_at']))
        unrelated = copy.deepcopy(audit)
        unrelated['changes'][0]['field'] = 'image_url'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'master.csv'
            proposal = Path(tmp) / 'audit.json'
            shutil.copy2(BASELINE, path)
            before = path.read_bytes()
            for invalid in [bad, unrelated]:
                proposal.write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    apply_updates(path, proposal)
                self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
