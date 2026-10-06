"""Classic Edition screen against the real API and the shared app.js; temporary files only.

Run explicitly: python -m pytest tests/test_classic_ui.py -q -o pythonpath=.
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

REVIEW = Path(__file__).resolve().parents[1] / '.verification-classic'
NO_PAGE_SCROLL = ('(() => { const m = document.querySelector(".classic-main"); const d = document.documentElement;'
                  ' return d.scrollWidth <= innerWidth && d.scrollHeight <= innerHeight'
                  ' && m.scrollWidth <= m.clientWidth && m.scrollHeight <= m.clientHeight; })()')
NO_HORIZONTAL_SCROLL = ('(() => { const m = document.querySelector(".classic-main");'
                        ' return document.documentElement.scrollWidth <= innerWidth && m.scrollWidth <= m.clientWidth; })()')
IN_VIEW = '(el) => { const r = el.getBoundingClientRect(); return r.top >= 0 && r.bottom <= innerHeight && r.right <= innerWidth; }'


@pytest.fixture
def ui(tmp_path):
    folder = tmp_path / 'files'
    folder.mkdir()
    jobs = JobManager(LocalState(tmp_path / 'state'))
    app = create_app(job_manager=jobs, folder_picker=lambda: str(folder), edition='classic')
    server = LocalServer(app, jobs)
    with pw.sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        server.start()
        page = browser.new_page(viewport={'width': 1100, 'height': 761}, reduced_motion='reduce')
        errors, external = [], []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('request', lambda request: external.append(request.url) if not request.url.startswith(server.url) else None)
        try:
            page.goto(server.url)
            pw.expect(page.locator('#saveSettings')).to_be_enabled()
            yield page, folder, jobs
        finally:
            browser.close()
            server.close()
        assert errors == []
        assert external == []


def view(page, name):
    page.locator(f'.nav-item[data-view="{name}"]').click()


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


def test_initial_screen_and_sidebar_views(ui):
    page, _, _ = ui
    assert page.locator('html').get_attribute('data-theme') == 'classic'
    assert page.title() == 'File Organizer Classic'
    pw.expect(page.locator('#classicViewOrganize')).to_be_visible()
    pw.expect(page.locator('#previewEmpty')).to_be_visible()
    pw.expect(page.locator('#previewButton')).to_be_disabled()
    pw.expect(page.locator('#organizeButton')).to_be_disabled()
    pw.expect(page.locator('.step[data-step="1"]')).to_have_attribute('aria-current', 'step')
    # Botanical engravings are loaded locally and never intercept clicks.
    for selector in ['.botanical-sidebar', '.botanical-header', '.botanical-card', '.botanical-sprig']:
        style = page.locator(selector).evaluate('(el) => { const s = getComputedStyle(el); return [s.pointerEvents, s.maskImage || s.webkitMaskImage]; }')
        assert style[0] == 'none' and '/static/classic/botanical/' in style[1], (selector, style)
    for name, shown in [('history', '#classicViewHistory'), ('help', '#classicViewHelp'), ('organize', '#classicViewOrganize')]:
        view(page, name)
        pw.expect(page.locator(shown)).to_be_visible()
        assert page.locator('.classic-main .view:visible').count() == 1
        pw.expect(page.locator(f'.nav-item[data-view="{name}"]')).to_have_attribute('aria-current', 'page')
        assert page.locator('.nav-item[aria-current="page"]').count() == 1
        assert page.evaluate('document.activeElement.tagName') == 'H1'
    view(page, 'history')
    pw.expect(page.locator('#historyEmpty')).to_be_visible()
    pw.expect(page.locator('#classicLatestPath')).to_have_text('まだ整理履歴はありません。')
    pw.expect(page.locator('#undoLatest')).to_be_disabled()


def test_type_preview_folder_list_organize_and_undo_from_history(ui):
    page, folder, jobs = ui
    for name in ['a.jpg', 'b.jpg', 'c.png', 'memo.txt', 'report.pdf', 'song.mp3', 'keep.tmp']:
        (folder / name).write_text('temporary')
    (folder / '画像').mkdir()
    (folder / '画像/a.jpg').write_text('existing')
    page.locator('#selectFolderButton').click()
    pw.expect(page.locator('#folderPath')).to_have_value(str(folder))
    page.locator('input[value="type"]').check()
    page.locator('#excludedExtensions').fill('.tmp')
    preview(page)
    pw.expect(page.locator('#planCount')).to_have_text('6')
    pw.expect(page.locator('#excludedCount')).to_contain_text('1')
    # 移動先フォルダー: counted from the rendered destinations; 画像 already exists but still counts.
    pw.expect(page.locator('#classicFolderCount')).to_have_text('3')
    pw.expect(page.locator('#classicFolderTotal')).to_have_text('全3個')
    items = page.locator('#classicFolderList li')
    pw.expect(items).to_have_count(3)
    assert [items.nth(i).inner_text().split('\n')[0] for i in range(3)][0] == '画像'
    pw.expect(items.first).to_contain_text('3 件')
    pw.expect(page.locator('#previewRows')).to_contain_text('a_1.jpg')
    # Cancelling keeps the files where they are.
    page.locator('#organizeButton').click()
    page.locator('#confirmDialog button[value="cancel"]').click()
    assert (folder / 'a.jpg').is_file()
    organize(page)
    pw.expect(page.locator('#successCount')).to_have_text('6')
    pw.expect(page.locator('#classicResultFolderTotal')).to_have_text('全3個')
    assert (folder / '画像/a_1.jpg').read_text() == 'temporary'
    assert (folder / '画像/a.jpg').read_text() == 'existing'
    # The "履歴" link in the result footer is navigation only.
    page.locator('#resultSection .link-button[data-view="history"]').click()
    pw.expect(page.locator('#classicViewHistory')).to_be_visible()
    pw.expect(page.locator('#classicLatestPath')).to_have_text(str(folder))
    pw.expect(page.locator('#classicLatestMeta')).to_contain_text('ファイル種類別')
    pw.expect(page.locator('#classicLatestMeta .status-pill')).to_have_text('整理完了')
    pw.expect(page.locator('.history-card')).to_have_count(1)
    undo(page)
    for name in ['a.jpg', 'b.jpg', 'c.png', 'memo.txt', 'report.pdf', 'song.mp3']:
        assert (folder / name).read_text() == 'temporary'
    assert (folder / '画像/a.jpg').read_text() == 'existing'
    pw.expect(page.locator('#undoLatest')).to_be_disabled()
    # Undo resets the organize view exactly as in Simple.
    view(page, 'organize')
    pw.expect(page.locator('#previewEmpty')).to_be_visible()
    assert jobs.state.settings() == {'rule': 'type', 'excluded_extensions': ['.tmp']}


def test_errors_are_visible_from_every_view(ui):
    page, folder, _ = ui
    (folder / 'sample.txt').write_text('temporary')
    page.locator('#folderPath').fill(str(folder))
    preview(page)
    organize(page)
    view(page, 'history')
    page.route('**/undo-preview', lambda route: route.abort())
    page.locator('#undoLatest').click()
    pw.expect(page.locator('#errorBanner')).to_be_visible()
    pw.expect(page.locator('#classicViewHistory')).to_be_visible()
    assert page.locator('#errorBanner').evaluate(IN_VIEW)
    page.unroute('**/undo-preview')
    page.locator('#closeError').click()
    pw.expect(page.locator('#errorBanner')).to_be_hidden()
    assert (folder / 'txt/sample.txt').is_file()
    # Preview failures (missing folder) still use the shared app.js messages.
    view(page, 'organize')
    page.locator('#startOverButton').click()
    page.locator('#folderPath').fill(str(folder / 'missing'))
    page.locator('#previewButton').click()
    pw.expect(page.locator('#previewFailureList')).to_contain_text('存在しません')
    pw.expect(page.locator('#classicFolderList')).to_contain_text('移動予定はありません')
    pw.expect(page.locator('#organizeButton')).to_be_disabled()


def test_running_job_survives_view_switching(ui, monkeypatch):
    page, folder, jobs = ui
    (folder / 'sample.txt').write_text('temporary')
    release = threading.Event()
    original = jobs._run
    def delayed(*args):
        assert release.wait(15)
        original(*args)
    monkeypatch.setattr(jobs, '_run', delayed)
    page.locator('#folderPath').fill(str(folder))
    preview(page)
    organize_click = page.locator('#organizeButton')
    organize_click.click()
    page.locator('#confirmStartButton').click()
    try:
        pw.expect(page.locator('#progressSection')).to_be_visible()
        pw.expect(page.locator('.nav-busy')).to_be_visible()
        view(page, 'history')
        # Locks hold in other views too: Undo stays disabled while organizing.
        pw.expect(page.locator('#undoLatest')).to_be_disabled()
        pw.expect(page.locator('#refreshHistory')).to_be_disabled()
        view(page, 'help')
        view(page, 'organize')
        pw.expect(page.locator('#progressSection')).to_be_visible()
        pw.expect(page.locator('#folderPath')).to_be_disabled()
        pw.expect(page.locator('input[value="type"]')).to_be_disabled()
        view(page, 'history')
        release.set()
        # Completion while another view is open: history refreshes, view does not jump.
        pw.expect(page.locator('.history-card')).to_have_count(1, timeout=15000)
        pw.expect(page.locator('#classicViewHistory')).to_be_visible()
        pw.expect(page.locator('#undoLatest')).to_be_enabled()
        view(page, 'organize')
        pw.expect(page.locator('#resultSection')).to_be_visible()
        pw.expect(page.locator('.nav-busy')).to_be_hidden()
        assert len(jobs._jobs) == 1
    finally:
        release.set()


def test_layout_sizes_keyboard_and_review_images(ui):
    page, folder, _ = ui
    REVIEW.mkdir(exist_ok=True)
    assert page.evaluate(NO_PAGE_SCROLL)
    page.screenshot(path=str(REVIEW / 'classic-initial-1100.png'))
    # Disabled primary is neutral; enabled primary is the deep green accent.
    assert page.locator('#previewButton').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(231, 223, 208)'
    page.locator('input[value="extension"]').focus()
    page.keyboard.press('ArrowRight')
    pw.expect(page.locator('input[value="type"]')).to_be_checked()
    assert page.locator('.rule-card').nth(1).evaluate('(el) => getComputedStyle(el).outlineStyle') != 'none'
    assert page.locator('.button').first.evaluate('(el) => getComputedStyle(el).transitionDuration') == '0s'
    page.locator('input[value="type"]').blur()
    for index in range(40):
        (folder / f'{index:02d}_report_{"long_name_" * (index % 5)}.{["txt", "jpg", "pdf", "mp3"][index % 4]}').write_text('temporary')
    page.locator('#folderPath').fill(str(folder))
    pw.expect(page.locator('#previewButton')).to_be_enabled()
    assert page.locator('#previewButton').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(62, 90, 53)'
    preview(page)
    # After preview, the run button leads and "整理予定を見る" steps back to secondary.
    assert page.locator('#organizeButton').evaluate('(el) => getComputedStyle(el).backgroundColor') == 'rgb(62, 90, 53)'
    assert page.locator('#previewButton').evaluate('(el) => getComputedStyle(el).backgroundColor') != 'rgb(62, 90, 53)'
    assert page.evaluate(NO_PAGE_SCROLL)
    assert page.locator('#organizeButton').evaluate(IN_VIEW)
    # Type rule (chosen by the arrow key above): txt and pdf both go to 文書 → 画像 / 文書 / 音声.
    pw.expect(page.locator('#classicFolderCount')).to_have_text('3')
    page.screenshot(path=str(REVIEW / 'classic-preview-1100.png'))
    page.set_viewport_size({'width': 800, 'height': 600})
    assert page.evaluate(NO_HORIZONTAL_SCROLL)
    # Icon sidebar keeps accessible names.
    assert page.locator('.nav-item[data-view="history"]').evaluate('(el) => el.getBoundingClientRect().width') <= 72
    pw.expect(page.get_by_role('button', name='履歴', exact=False).first).to_be_visible()
    page.screenshot(path=str(REVIEW / 'classic-preview-800.png'))
    page.set_viewport_size({'width': 1100, 'height': 761})
    organize(page)
    assert page.evaluate(NO_PAGE_SCROLL)
    assert page.locator('#startOverButton').evaluate(IN_VIEW)
    pw.expect(page.locator('.step[data-step="3"]')).to_have_attribute('aria-current', 'step')
    page.screenshot(path=str(REVIEW / 'classic-done-1100.png'))
    view(page, 'history')
    assert page.evaluate(NO_PAGE_SCROLL)
    assert page.locator('#undoLatest').evaluate(IN_VIEW)
    page.screenshot(path=str(REVIEW / 'classic-history-1100.png'))
    view(page, 'help')
    page.screenshot(path=str(REVIEW / 'classic-help-1100.png'))
    # Short desktop windows (the window is fitted to small work areas): the sidebar never scrolls
    # and the brand stays on one line.
    sidebar_fits = '(() => { const s = document.querySelector(".sidebar"); return s.scrollHeight <= s.clientHeight; })()'
    page.set_viewport_size({'width': 1100, 'height': 600})
    assert page.evaluate(sidebar_fits)
    assert page.locator('.brand-name').evaluate('(el) => el.getBoundingClientRect().height') < 30
    page.set_viewport_size({'width': 800, 'height': 600})
    assert page.evaluate(sidebar_fits)
    for name in ['help', 'history', 'organize']:
        view(page, name)
        assert page.evaluate(NO_HORIZONTAL_SCROLL), name
        page.screenshot(path=str(REVIEW / f'classic-{name}-800.png'))
