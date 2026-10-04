"""Actual Vanilla JS flows against the existing API; temporary files only.

Run explicitly: python -m pytest tests/test_simple_ui.py -q -o pythonpath=.
Uses installed Microsoft Edge; no downloaded browser or online UI dependency.
"""
import threading
from pathlib import Path

import pytest

pw = pytest.importorskip('playwright.sync_api')
from desktop_app import LocalServer
from local_state import LocalState
from organizer_service import JobManager
from web_app import create_app


@pytest.fixture
def ui(tmp_path):
    folder = tmp_path / 'files'
    folder.mkdir()
    jobs = JobManager(LocalState(tmp_path / 'state'))
    app = create_app(job_manager=jobs, folder_picker=lambda: str(folder))
    server = LocalServer(app, jobs)
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        server.start()
        page = browser.new_page(viewport={'width': 1100, 'height': 800}, reduced_motion='reduce')
        errors, external = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url) if not request.url.startswith(server.url) else None)
        try:
            page.goto(server.url)
            pw.expect(page.locator('#saveSettings')).to_be_enabled()
            yield page, folder, jobs, tmp_path
        finally:
            browser.close()
            server.close()
        assert errors == []
        assert external == []


def preview(page):
    page.locator('#previewButton').click()
    pw.expect(page.locator('#previewContent')).to_be_visible()
    pw.expect(page.locator('#previewButton')).to_be_enabled()


def organize(page):
    page.locator('#organizeButton').click()
    pw.expect(page.locator('#confirmDialog')).to_be_visible()
    page.locator('#confirmStartButton').click()
    pw.expect(page.locator('#resultSection')).to_be_visible(timeout=15000)


def undo(page):
    page.locator('#undoLatest').click()
    pw.expect(page.locator('#undoDialog')).to_be_visible()
    page.locator('#undoDialog button[value="undo"]').click()
    pw.expect(page.locator('#undoResult')).to_contain_text('成功', timeout=15000)
    pw.expect(page.locator('#folderPath')).to_be_enabled()


def test_extension_flow_settings_collision_undo(ui):
    page, folder, jobs, _ = ui
    (folder / 'sample.txt').write_text('content')
    (folder / 'keep.tmp').write_text('excluded')
    (folder / 'txt').mkdir()
    (folder / 'txt/sample.txt').write_text('existing')
    pw.expect(page.locator('#previewButton')).to_be_disabled()
    pw.expect(page.locator('#organizeButton')).to_be_disabled()
    pw.expect(page.locator('#historyEmpty')).to_be_visible()
    page.locator('#selectFolderButton').click()
    pw.expect(page.locator('#folderPath')).to_have_value(str(folder))
    page.locator('#excludedExtensions').fill('.tmp')
    page.locator('#saveSettings').click()
    pw.expect(page.locator('#settingsStatus')).to_have_text('設定を保存しました。')
    page.reload()
    pw.expect(page.locator('#excludedExtensions')).to_have_value('.tmp')
    page.locator('#folderPath').fill(str(folder))
    preview(page)
    pw.expect(page.locator('#planCount')).to_have_text('1')
    pw.expect(page.locator('#excludedCount')).to_contain_text('1')
    pw.expect(page.locator('#previewRows')).to_contain_text('sample_1.txt')
    # Cancellation must preserve files and permit another confirmation.
    page.locator('#organizeButton').click()
    page.locator('#confirmDialog button[value="cancel"]').click()
    assert (folder / 'sample.txt').is_file()
    organize(page)
    pw.expect(page.locator('#successCount')).to_have_text('1')
    pw.expect(page.locator('.history-card')).to_have_count(1)
    assert (folder / 'txt/sample_1.txt').read_text() == 'content'
    assert (folder / 'keep.tmp').is_file()
    undo(page)
    assert (folder / 'sample.txt').read_text() == 'content'
    assert (folder / 'txt/sample.txt').read_text() == 'existing'
    pw.expect(page.locator('#undoLatest')).to_be_disabled()
    assert jobs.state.settings()['excluded_extensions'] == ['.tmp']


def test_type_rule_invalidation_and_partial_undo(ui):
    page, folder, jobs, _ = ui
    (folder / 'sample.txt').write_text('original')
    (folder / 'photo.jpg').write_bytes(b'temporary image data')
    page.locator('#folderPath').fill(str(folder))
    preview(page)
    page.locator('input[value="type"]').check()
    pw.expect(page.locator('#organizeButton')).to_be_disabled()
    preview(page)
    plans = page.locator('#previewRows').inner_text()
    assert '文書' in plans and '画像' in plans
    organize(page)
    # Occupied original path must never be overwritten by Undo.
    (folder / 'sample.txt').write_text('replacement')
    undo(page)
    pw.expect(page.locator('#undoResult')).to_contain_text('失敗 1 件')
    pw.expect(page.locator('#undoResult li')).to_have_count(1)
    assert (folder / 'sample.txt').read_text() == 'replacement'
    assert (folder / 'photo.jpg').is_file()
    page.reload()
    pw.expect(page.locator('input[value="type"]')).to_be_checked()
    assert jobs.state.settings()['rule'] == 'type'


def test_errors_zero_preview_large_list_and_small_window(ui):
    page, folder, _, tmp_path = ui
    page.locator('#folderPath').fill(str(tmp_path / 'missing'))
    page.locator('#previewButton').click()
    # The existing API reports invalid folders as preview failures (HTTP 200).
    pw.expect(page.locator('#previewFailures')).to_be_visible()
    pw.expect(page.locator('#previewFailureList')).to_contain_text('存在しません')
    pw.expect(page.locator('#organizeButton')).to_be_disabled()
    page.route('**/api/preview', lambda route: route.abort())
    page.locator('#previewButton').click()
    pw.expect(page.locator('#errorBanner')).to_be_visible()
    page.unroute('**/api/preview')
    page.locator('#closeError').click()
    page.locator('#folderPath').fill(str(folder))
    preview(page)
    pw.expect(page.locator('#planCount')).to_have_text('0')
    pw.expect(page.locator('#organizeButton')).to_be_disabled()
    for index in range(120):
        (folder / (f'{index:03d}_' + 'long_name_' * 12 + '.txt')).write_text('temporary')
    preview(page)
    pw.expect(page.locator('#previewRows tr')).to_have_count(120)
    page.set_viewport_size({'width': 800, 'height': 600})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert page.locator('#previewRows').evaluate('(el) => el.closest(".table-wrap").clientHeight <= 340')


def test_running_guards_and_polling_recovery(ui, monkeypatch):
    page, folder, jobs, _ = ui
    (folder / 'sample.txt').write_text('temporary')
    release = threading.Event()
    original = jobs._run
    def delayed(*args):
        assert release.wait(15)
        original(*args)
    monkeypatch.setattr(jobs, '_run', delayed)
    page.locator('#folderPath').fill(str(folder))
    preview(page)
    page.locator('#organizeButton').click()
    page.route('**/api/jobs/*', lambda route: route.abort())
    page.locator('#confirmStartButton').click()
    try:
        pw.expect(page.locator('#progressSection')).to_be_visible()
        pw.expect(page.locator('#retryProgress')).to_be_visible()
        pw.expect(page.locator('#folderPath')).to_be_disabled()
        pw.expect(page.locator('#organizeButton')).to_be_disabled()
        pw.expect(page.locator('input[value="type"]')).to_be_disabled()
        assert len(jobs._jobs) == 1
        page.unroute('**/api/jobs/*')
        release.set()
        page.locator('#retryProgress').click()
        pw.expect(page.locator('#resultSection')).to_be_visible(timeout=15000)
        pw.expect(page.locator('#progressPercent')).to_have_text('100%')
        pw.expect(page.locator('#folderPath')).to_be_enabled()
        assert len(jobs._jobs) == 1
    finally:
        release.set()


def test_layout_keyboard_offline_and_review_images(ui):
    page, folder, _, _ = ui
    review = Path(__file__).resolve().parents[1] / '.verification-simple'
    review.mkdir(exist_ok=True)
    page.screenshot(path=str(review / 'simple-initial-1100.png'), full_page=True)
    assert page.locator('html').get_attribute('data-theme') == 'simple'
    # Workspace design: a disabled primary is neutral grey, never a faded accent.
    pw.expect(page.locator('#previewButton')).to_be_disabled()
    assert page.locator('#previewButton').evaluate('(el) => getComputedStyle(el).backgroundColor') != 'rgb(49, 89, 184)'
    # Native radio keyboard navigation remains available.
    page.locator('input[value="extension"]').focus()
    page.keyboard.press('ArrowRight')
    pw.expect(page.locator('input[value="type"]')).to_be_checked()
    assert page.locator('input[value="type"]').evaluate('(el) => getComputedStyle(el).outlineStyle') != 'none'
    assert page.locator('.button').first.evaluate('(el) => getComputedStyle(el).transitionDuration') == '0s'
    page.locator('input[value="type"]').blur()
    for name in ['report.pdf', 'notes.txt', 'photo.jpg']:
        (folder / name).write_text('temporary review data')
    page.locator('#folderPath').fill(str(folder))
    # An enabled primary action uses the accent colour.
    pw.expect(page.locator('#previewButton')).to_be_enabled()
    assert page.locator('#previewButton').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(49, 89, 184)'
    preview(page)
    # After preview, "整理を実行" takes over as the accent-coloured primary action.
    assert page.locator('#organizeButton').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(49, 89, 184)'
    page.screenshot(path=str(review / 'simple-preview-1100.png'), full_page=True)
    page.set_viewport_size({'width': 800, 'height': 600})
    page.screenshot(path=str(review / 'simple-preview-800.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')


def test_workspace_fits_default_window_without_page_scroll(ui):
    """1100x800 window ≈ 1100x761 web area: main actions stay visible without scrolling."""
    page, folder, _, _ = ui
    page.set_viewport_size({'width': 1100, 'height': 761})
    in_view = '(el) => { const r = el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight; }'
    no_scroll = 'document.documentElement.scrollHeight <= innerHeight && document.documentElement.scrollWidth <= innerWidth'
    assert page.evaluate(no_scroll)
    assert page.locator('#previewButton').evaluate(in_view)
    for index in range(40):
        (folder / f'{index:02d}_report.txt').write_text('temporary')
    page.locator('#folderPath').fill(str(folder))
    preview(page)
    assert page.evaluate(no_scroll)
    assert page.locator('#organizeButton').evaluate(in_view)
    organize(page)
    # Result replaces the preview in the right pane; the earlier views are not stacked below it.
    pw.expect(page.locator('#previewSection')).to_be_hidden()
    pw.expect(page.locator('#progressSection')).to_be_hidden()
    assert page.evaluate(no_scroll)
    for selector in ['#startOverButton', '#undoLatest']:
        assert page.locator(selector).evaluate(in_view)
    undo(page)
    pw.expect(page.locator('#previewSection')).to_be_visible()
    # The previous Undo message stays readable while previewing, and is cleared
    # once a new organization starts so it cannot be mistaken for the new run.
    pw.expect(page.locator('#undoResult')).to_be_visible()
    preview(page)
    pw.expect(page.locator('#undoResult')).to_be_visible()
    organize(page)
    pw.expect(page.locator('#undoResult')).to_be_hidden()
    pw.expect(page.locator('#successCount')).to_have_text('40')
