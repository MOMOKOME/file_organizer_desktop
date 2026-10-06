"""Classic Edition wiring: edition detection, template choice and the shared DOM contract.

Classic only swaps the screen. These tests keep the Simple default untouched and check that
the Classic template carries every id/attribute that the shared static/app.js depends on.
"""
import shutil
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

import pytest

import app_config
from app_config import resource_path
from web_app import create_app

ROOT = Path(__file__).resolve().parents[1]

# UI_DESIGN_HANDOFF.md "JavaScriptとの接続" table, plus ids app.js reads directly.
CONTRACT_IDS = """
folderPath selectFolderButton previewButton organizationRule excludedExtensions saveSettings settingsStatus
previewSection previewEmpty previewContent previewBadge previewRows planCount excludedCount previewFailureCount
previewFailures previewFailureList previewNotice previewNoticeText organizeButton
progressSection currentFile progressPercent progressBar progressCount retryProgress progressStatus
resultSection resultIcon resultHeading resultDescription successCount failureCount processedCount
successResults failureResults successRows failureRows startOverButton
historyRows historyEmpty refreshHistory undoLatest undoAvailability undoResult
errorBanner errorMessage closeError appStatus
confirmDialog confirmCount confirmStartButton undoDialog undoFiles undoCount
""".split()


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.elements = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))

    def find(self, **wanted):
        return [(tag, attrs) for tag, attrs in self.elements
                if all(attrs.get(key) == value for key, value in wanted.items())]

    def by_class(self, name):
        return [(tag, attrs) for tag, attrs in self.elements if name in (attrs.get('class') or '').split()]


def home(edition, **kwargs):
    client = create_app(folder_picker=lambda: None, edition=edition, **kwargs).test_client()
    response = client.get('/')
    assert response.status_code == 200
    return response.get_data(as_text=True)


@pytest.mark.parametrize('environment, expected', [
    (None, 'simple'), ('classic', 'classic'), (' Classic ', 'classic'), ('simple', 'simple'), ('cyber', 'simple'),
])
def test_development_edition_comes_from_environment(monkeypatch, environment, expected):
    monkeypatch.delattr(sys, 'frozen', raising=False)
    if environment is None:
        monkeypatch.delenv(app_config.EDITION_ENV, raising=False)
    else:
        monkeypatch.setenv(app_config.EDITION_ENV, environment)
    assert app_config.detect_edition() == expected


@pytest.mark.parametrize('marker, expected', [(None, 'simple'), ('classic', 'classic'), ('classic\n', 'classic'), ('other', 'simple')])
def test_frozen_edition_uses_only_bundled_marker(monkeypatch, tmp_path, marker, expected):
    # A user's environment variable must never turn the Simple exe into Classic (or back).
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    monkeypatch.setenv(app_config.EDITION_ENV, 'simple' if expected == 'classic' else 'classic')
    if marker is not None:
        (tmp_path / app_config.EDITION_MARKER).write_text(marker, encoding='utf-8')
    assert app_config.detect_edition() == expected


def test_display_names_and_shared_storage():
    assert app_config.EDITIONS == {'simple': 'File Organizer', 'classic': 'File Organizer Classic'}
    # Shared engine identity: the data folder (and with it desktop.lock) is edition-independent.
    assert app_config.APP_NAME == 'File Organizer'
    assert app_config.user_data_directory().parts[-2:] == ('MOMONGA_Lab', 'FileOrganizer')


def test_simple_remains_the_default_page():
    html = home(None) if app_config.EDITION == 'simple' else home('simple')
    assert 'data-theme="simple"' in html and '整理予定プレビュー' in html
    assert 'classic' not in html


def test_classic_page_uses_its_own_assets():
    html = home('classic')
    assert 'data-theme="classic"' in html
    assert '<title>File Organizer Classic</title>' in html
    assert '/static/classic/classic.css' in html and '/static/style.css' not in html
    # app.js is shared and must load before classic.js.
    assert html.index('/static/app.js') < html.index('/static/classic/classic.js')
    assert 'Classic Edition' in html and 'v' + app_config.VERSION in html


@pytest.mark.parametrize('edition', ['simple', 'classic'])
def test_every_contract_id_exists_exactly_once(edition):
    page = Page(home(edition))
    counts = Counter(attrs['id'] for _, attrs in page.elements if 'id' in attrs)
    assert {name: counts[name] for name in CONTRACT_IDS if counts[name] != 1} == {}
    assert [name for name, count in counts.items() if count > 1] == []


def test_classic_keeps_contract_attributes():
    page = Page(home('classic'))
    tag, _ = page.find(id='organizationRule')[0]
    assert tag == 'fieldset'
    radios = page.find(name='organizationRule', type='radio')
    assert [attrs['value'] for _, attrs in radios] == ['extension', 'type']
    assert 'checked' in radios[0][1]
    for table_body in ('previewRows', 'successRows', 'failureRows'):
        assert page.find(id=table_body)[0][0] == 'tbody'
    assert page.find(id='historyRows')[0][0] == 'div'
    assert page.find(id='previewBadge')[0][0] == 'div'
    assert [attrs['data-step'] for _, attrs in page.by_class('step')] == ['1', '2', '3']
    assert page.by_class('step')[0][1].get('aria-current') == 'step'
    # Not in the id table but required by app.js (setOperationBusy / renderProgress).
    assert len(page.by_class('folder-panel')) == 1 and len(page.by_class('progress-track')) == 1
    assert page.find(id='progressSection')[0][1].get('aria-busy') == 'true'
    for name in ('progressSection', 'resultSection', 'previewContent', 'errorBanner', 'retryProgress',
                 'previewNotice', 'previewFailures', 'failureResults', 'successResults', 'undoResult', 'previewBadge'):
        assert 'hidden' in page.find(id=name)[0][1], name
    for name in ('previewButton', 'organizeButton', 'undoLatest'):
        assert 'disabled' in page.find(id=name)[0][1], name
    for name in ('errorBanner',):
        assert page.find(id=name)[0][1].get('role') == 'alert'
    for name in ('appStatus', 'settingsStatus', 'undoResult', 'progressStatus', 'resultDescription'):
        assert page.find(id=name)[0][1].get('role') == 'status', name
    assert page.find(id='folderPath')[0][1].get('aria-describedby') == 'folderHelp'
    assert len(page.find(**{'for': 'folderPath'})) == 1 and len(page.find(**{'for': 'excludedExtensions'})) == 1
    # Dialogs: form method=dialog and the returnValues app.js checks.
    assert len(page.find(method='dialog')) == 2
    assert [attrs.get('value') for tag, attrs in page.elements if tag == 'button' and 'value' in attrs] == \
        ['cancel', 'default', 'cancel', 'undo']
    assert page.find(id='confirmDialog')[0][0] == 'dialog' and page.find(id='undoDialog')[0][0] == 'dialog'
    # Every non-dialog button is an explicit type="button" (nothing submits by accident).
    for tag, attrs in page.elements:
        if tag == 'button' and 'value' not in attrs:
            assert attrs.get('type') == 'button', attrs


def test_classic_layout_contract():
    page = Page(home('classic'))
    # Exactly one view is shown at start; the history elements always exist in the DOM.
    assert 'hidden' not in page.find(id='classicViewOrganize')[0][1]
    assert 'hidden' in page.find(id='classicViewHistory')[0][1]
    assert 'hidden' in page.find(id='classicViewHelp')[0][1]
    nav = page.by_class('nav-item')
    assert [attrs['data-view'] for _, attrs in nav] == ['organize', 'history', 'help']
    assert [attrs.get('aria-current') for _, attrs in nav] == ['page', None, None]
    # Botanical decorations never carry content or catch clicks.
    decorations = page.by_class('botanical')
    assert len(decorations) == 4 and all(attrs.get('aria-hidden') == 'true' for _, attrs in decorations)


def test_classic_html_has_no_inline_colors_or_external_urls():
    source = (ROOT / 'templates/classic/index.html').read_text(encoding='utf-8')
    assert 'style=' not in source and 'fill="#' not in source and 'stroke="#' not in source
    for text in (source, (ROOT / 'static/classic/classic.css').read_text(encoding='utf-8'),
                 (ROOT / 'static/classic/classic.js').read_text(encoding='utf-8')):
        assert 'http://' not in text.replace('http://www.w3.org/2000/svg', '')
        assert 'https://' not in text
    assert 'innerHTML' not in (ROOT / 'static/classic/classic.js').read_text(encoding='utf-8')


def test_production_botanicals_have_no_generation_metadata():
    production = sorted((ROOT / 'static/classic/botanical').glob('*.svg'))
    assert [path.name for path in production] == ['card-fern.svg', 'empty-olive-sprig.svg', 'header-olive.svg', 'sidebar.svg']
    for path in production:
        text = path.read_text(encoding='utf-8')
        assert '<metadata' not in text and 'c2pa' not in text
        assert text.startswith('<svg xmlns="http://www.w3.org/2000/svg"')


def test_frozen_classic_bundle_serves_its_resources(monkeypatch, tmp_path):
    # Mirrors FileOrganizerClassic.spec: Classic template/static + shared app.js + marker only.
    shutil.copytree(resource_path('templates/classic'), tmp_path / 'templates/classic')
    shutil.copytree(resource_path('static/classic'), tmp_path / 'static/classic')
    shutil.copy2(resource_path('static/app.js'), tmp_path / 'static/app.js')
    (tmp_path / 'edition.txt').write_text('classic', encoding='utf-8')
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    assert app_config.detect_edition() == 'classic'
    client = create_app(data_directory=tmp_path / 'state', edition='classic').test_client()
    assert 'data-theme="classic"' in client.get('/').get_data(as_text=True)
    for name in ('app.js', 'classic/classic.css', 'classic/classic.js', 'classic/botanical/sidebar.svg',
                 'classic/botanical/header-olive.svg', 'classic/botanical/card-fern.svg',
                 'classic/botanical/empty-olive-sprig.svg'):
        assert client.get(f'/static/{name}').status_code == 200, name
