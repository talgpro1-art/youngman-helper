"""Apply only the explicit, evidence-backed price audit changes; no network calls."""
from pathlib import Path
import csv
import io
import json

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / 'vehicle_master.csv'
AUDIT = ROOT / 'data/sales_snapshot/price_audit_2026-11-03.json'


def apply_updates(master_path: Path = MASTER, audit_path: Path = AUDIT) -> None:
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    reader = csv.DictReader(io.StringIO(master_path.read_bytes().decode('utf-8-sig')))
    columns = reader.fieldnames
    rows = list(reader)
    keyed = {(r['brand'], r['model']): r for r in rows}
    if len(keyed) != len(rows):
        raise ValueError('Duplicate vehicle identity')
    evidence = {(r['brand'], r['model'], link['field']): link
                for r in audit['records'] if r['scope'] == 'candidate_top50'
                for link in r['links']}
    seen = set()
    # Check every precondition before writing anything, including partial reruns.
    for change in audit['changes']:
        key = (change['brand'], change['model'])
        field = change['field']
        cell = (*key, field)
        if field not in {'price_url', 'catalog_url', 'note'} or cell in seen or key not in keyed:
            raise ValueError('Invalid or duplicate scoped change')
        seen.add(cell)
        if not change['evidence_urls'] or not change['checked_at']:
            raise ValueError('Missing review evidence')
        if field != 'note':
            record = evidence.get(cell, {})
            if (record.get('mutation') != 'apply_verified_replacement'
                    or not record.get('replacement_document_content_verified')
                    or (record.get('existing_url'), record.get('proposed_url')) != (change['old'], change['new'])
                    or not change['new'].startswith('https://')):
                raise ValueError('Replacement content verification required')
        if keyed[key][field] not in {change['old'], change['new']}:
            raise ValueError(f'Exact old value changed: {key} {field}')
    for change in audit['changes']:
        keyed[(change['brand'], change['model'])][change['field']] = change['new']
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    content = output.getvalue().encode('utf-8-sig')
    if content != master_path.read_bytes():
        master_path.write_bytes(content)


if __name__ == '__main__':
    apply_updates()
