"""Audit coverage, exact guarded changes, and preservation of held/unrelated fields."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import pandas as pd

from apply_reviewed_price_updates import apply_updates

SNAPSHOT = Path(__file__).resolve().parents[1] / 'data/sales_snapshot'
AUDIT = SNAPSHOT / 'price_audit_2026-11-03.json'
# Freeze the historical audit against the exact pre-refresh deployed master.
MASTER = SNAPSHOT / 'history/vehicle_master_before_2026-11-12-domestic10-import10.csv'

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


class CurrentPriceAuditUpdateTests(unittest.TestCase):
    audit_path = SNAPSHOT / 'price_audit_2026-11-12.json'
    baseline_path = SNAPSHOT / 'history/vehicle_master_before_2026-11-12-price-audit.csv'
    master_path = SNAPSHOT.parents[1] / 'vehicle_master.csv'

    def test_complete_current_coverage_and_exact_changes(self):
        audit = json.loads(self.audit_path.read_text())
        before, after = frame(self.baseline_path), frame(self.master_path)
        self.assertEqual(before.index.tolist(), after.index.tolist())
        self.assertEqual(before.columns.tolist(), after.columns.tolist())
        self.assertEqual(len(audit['records']), 52)
        self.assertEqual(sum(len(r['links']) for r in audit['records']), 53)
        records = [r for r in audit['records'] if r['scope'] == 'candidate_top50']
        self.assertEqual(len(records), 50)
        self.assertEqual({(r['brand'], r['model']) for r in records}, set(after.index))
        expected = {(c['brand'], c['model'], c['field']) for c in audit['changes']}
        self.assertEqual(len(expected), len(audit['changes']))
        expected_models = {('벤츠', 'E-Class'), ('벤츠', 'The New S-Class'), ('르노', '아르카나'), ('르노', '필랑트')}
        self.assertEqual(expected, {(*key, field) for key in expected_models for field in ['price_url', 'note']})
        self.assertTrue(all(field in {'price_url', 'catalog_url', 'note'} for _, _, field in expected))
        actual = {(*key, col) for key in before.index for col in before.columns if before.loc[key, col] != after.loc[key, col]}
        self.assertEqual(actual, expected)
        for change in audit['changes']:
            key = (change['brand'], change['model'])
            self.assertEqual(before.loc[key, change['field']], change['old'])
            self.assertEqual(after.loc[key, change['field']], change['new'])
            self.assertTrue(change['checked_at'])
            self.assertTrue(change['evidence_urls'])
        for record in records:
            key = (record['brand'], record['model'])
            for link in record['links']:
                self.assertTrue(link['checked_at'])
                self.assertTrue(link['evidence_urls'])
                if (*key, link['field']) not in expected:
                    self.assertEqual(after.loc[key, link['field']], link['existing_url'])

    def test_link_history_preserved_and_new_checks_match_exact_evidence(self):
        with (self.master_path.parent / 'data/link_status.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 101)
        original = json.dumps(rows[:90], sort_keys=True, ensure_ascii=False).encode()
        self.assertEqual(hashlib.sha256(original).hexdigest(), '8bc228c65ae0a80bd7674d6256877cf735b2d36e180935a55a6c0fb13d0a1924')
        added = rows[90:]
        self.assertEqual({r['model'] for r in added}, {'Model Y', 'Model 3', 'E-Class', '5 Series', 'X3', 'The New S-Class', 'X5', 'GLC-Class', '아르카나', '그랑 콜레오스', '필랑트'})
        self.assertEqual(len({(r['vehicle'], r['url']) for r in added}), 11)
        audit = json.loads(self.audit_path.read_text())
        master = frame(self.master_path)
        for row in added:
            current = master.loc[(row['brand'], row['model'])]
            self.assertEqual(row['url'], current.price_url)
            self.assertEqual(row['vehicle'], current.vehicle)
            self.assertEqual(int(row['rank']), int(current['rank']))
            self.assertEqual(row['checked_at'], audit['checked_at'])
            record = next(r for r in audit['records'] if r['vehicle'] == row['vehicle'])
            link = next(l for l in record['links'] if l['field'] == 'price_url' and l['proposed_url'] == row['url'])
            self.assertTrue(link['current_official_content_verified'])
            self.assertEqual(row['doc_type'], '가격표')
            self.assertEqual(row['error'], '')
            if row['model'] in {'Model Y', 'Model 3'}:
                self.assertEqual(row['verification_status'], 'OFFICIAL_PAGE')
            else:
                self.assertEqual(row['verification_status'], 'MATCHED')
                self.assertEqual(row['content_type'], 'application/pdf')
                if link.get('document_sha256'):
                    self.assertEqual(row['sha256'], link['document_sha256'])
                    self.assertEqual(int(row['content_length']), link['document_bytes'])
                    if 'http_status' in link:
                        self.assertEqual(int(row['status_code']), link['http_status'])
                else:
                    self.assertEqual(len(row['sha256']), 64)
                    self.assertGreater(int(row['content_length']), 0)


    def test_current_rebuild_and_repeat_preserve_bytes_and_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'master.csv'
            shutil.copy2(self.baseline_path, path)
            apply_updates(path, self.audit_path)
            self.assertEqual(path.read_bytes(), self.master_path.read_bytes())
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            apply_updates(path, self.audit_path)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_current_changed_precondition_rejects_all_writes(self):
        audit = json.loads(self.audit_path.read_text())
        change = audit['changes'][0]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'master.csv'
            data = pd.read_csv(self.baseline_path, dtype=str).fillna('')
            data.loc[data.brand.eq(change['brand']) & data.model.eq(change['model']), change['field']] = 'concurrent edit'
            data.to_csv(path, index=False, encoding='utf-8-sig')
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            with self.assertRaisesRegex(ValueError, 'Exact old value changed'):
                apply_updates(path, self.audit_path)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)

    def test_current_unverified_replacement_rejects_all_writes(self):
        audit = json.loads(self.audit_path.read_text())
        change = next(c for c in audit['changes'] if c['field'] != 'note')
        record = next(r for r in audit['records'] if (r['brand'], r['model']) == (change['brand'], change['model']))
        link = next(l for l in record['links'] if l['field'] == change['field'])
        link['replacement_document_content_verified'] = False
        with tempfile.TemporaryDirectory() as tmp:
            path, proposal = Path(tmp) / 'master.csv', Path(tmp) / 'audit.json'
            shutil.copy2(self.baseline_path, path)
            proposal.write_text(json.dumps(audit))
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            with self.assertRaisesRegex(ValueError, 'Replacement content verification required'):
                apply_updates(path, proposal)
            self.assertEqual((path.read_bytes(), path.stat().st_mtime_ns), before)


if __name__ == '__main__':
    unittest.main()
