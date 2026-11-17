import importlib.util
import json
import io
from types import SimpleNamespace
from pypdf import PdfWriter
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
checker = load('check_price_links')
notices = load('update_notifications')

class StatusTests(unittest.TestCase):
    def test_access_and_transport_are_not_broken_links(self):
        for code in (401, 403, 429):
            self.assertEqual(checker.semantic_verification('X5', 'https://example.com/a.pdf', {'status_code': code})[0], 'ACCESS_RESTRICTED')
        for code in (500, 502, 'ERROR'):
            self.assertEqual(checker.semantic_verification('X5', 'https://example.com/a.pdf', {'status_code': code})[0], 'CHECK_UNAVAILABLE')
        self.assertEqual(checker.semantic_verification('X5', 'https://example.com/a.pdf', {}, 'Read timed out')[0], 'CHECK_UNAVAILABLE')
        for code in (404,410):
            self.assertEqual(checker.semantic_verification('X5', 'https://example.com/a.pdf', {'status_code':code})[0], 'ERROR')
    def test_pdf_semantics_preserved(self):
        url='https://example.com/a.pdf'
        self.assertEqual(checker.semantic_verification('X5',url,{'status_code':200,'_pdf_text':'BMW X5 price'})[0],'MATCHED')
        self.assertEqual(checker.semantic_verification('X5',url,{'status_code':200,'_pdf_text':'BMW X3 price'})[0],'MISMATCH')
        self.assertEqual(checker.semantic_verification('X5',url,{'status_code':200,'_pdf_text':''})[0],'TEXT_UNAVAILABLE')
    def test_real_pdf_bytes_confirm_download_even_without_text(self):
        writer = PdfWriter(); writer.add_blank_page(width=100, height=100)
        stream = io.BytesIO(); writer.write(stream)
        response = SimpleNamespace(ok=True, status_code=200, content=stream.getvalue(), headers={"Content-Type":"application/pdf"})
        checker.fetch_hash.cache_clear()
        with patch.object(checker.requests, "get", return_value=response):
            info = checker.fetch_hash('https://example.com/valid.pdf')
        self.assertEqual(info['download_status'], 'VERIFIED_PDF')
        self.assertEqual(info['pdf_page_count'], 1)
        self.assertEqual(checker.semantic_verification('X5','https://example.com/valid.pdf',info)[0], 'TEXT_UNAVAILABLE')
        response.content = b'%PDF-1.7 broken'
        checker.fetch_hash.cache_clear()
        with patch.object(checker.requests, "get", return_value=response):
            info = checker.fetch_hash('https://example.com/broken.pdf')
        self.assertEqual(info['download_status'], 'INVALID_PDF')
        self.assertEqual(checker.semantic_verification('X5','https://example.com/broken.pdf',info)[0], 'INVALID_PDF')
    def test_refresh_failure_preserves_news(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'notifications.json'; status=Path(d)/'refresh.json'
            target.write_text('[{"title":"keep me"}]')
            with patch.object(notices,'NOTI_FILE',target), patch.object(notices,'REFRESH_FILE',status), patch.object(notices,'load_verified_notifications',side_effect=OSError('offline')):
                notices.main()
            self.assertEqual(target.read_text(),'[{"title":"keep me"}]')
            self.assertEqual(json.loads(status.read_text())['status'],'failed')
    def test_success_has_separate_check_time(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'notifications.json'; status=Path(d)/'refresh.json'
            news=[{'article_date':'2026-11-11','title':'article'}]
            with patch.object(notices,'NOTI_FILE',target), patch.object(notices,'REFRESH_FILE',status), patch.object(notices,'load_verified_notifications',return_value=news):
                notices.main()
            self.assertEqual(json.loads(target.read_text()),news)
            self.assertEqual(json.loads(status.read_text())['status'],'success')
            self.assertIn('+09:00',json.loads(status.read_text())['checked_at'])

if __name__=='__main__': unittest.main()
