from app.settings import settings
from core.policy_loader import iter_supported_files, load_chunks, parse_policy


def test_corpus_has_required_formats_and_size():
    files = list(iter_supported_files(settings.corpus_dir))
    suffixes = {p.suffix.lower() for p in files}
    assert len(files) == 16
    assert ".md" in suffixes
    assert ".html" in suffixes
    assert ".txt" in suffixes
    assert len(load_chunks(settings.corpus_dir)) > 40


def test_html_calendar_parses():
    path = settings.corpus_dir / "15_holiday_calendar_2026.html"
    doc_id, title, sections = parse_policy(path)
    assert doc_id == "MF-CAL-2026"
    assert "Holiday Calendar" in title
    assert any("Calendar" in heading for heading, _ in sections)
