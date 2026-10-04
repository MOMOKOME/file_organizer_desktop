import sys
import threading
import time
import shutil
import socket
import subprocess
from urllib.request import urlopen

import pytest

from app_config import resource_path, user_data_directory
from desktop_app import AlreadyRunning, InstanceLock, LocalServer, fit_window, run_desktop, windows_work_area
from local_state import LocalState
from organizer_service import JobManager, PreviewStore
from web_app import create_app


def test_paths(monkeypatch, tmp_path):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    assert user_data_directory() == tmp_path / 'MOMONGA_Lab' / 'FileOrganizer'
    assert resource_path('templates/index.html').is_file()
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    assert resource_path('static/app.js') == tmp_path / 'static/app.js'


def test_explicit_development_storage(tmp_path):
    state = LocalState(tmp_path / 'dev')
    state.save_settings()
    assert (tmp_path / 'dev/state.sqlite3').is_file()


def test_instance_lock_rejects_and_releases(tmp_path):
    with InstanceLock(tmp_path):
        with pytest.raises(AlreadyRunning):
            with InstanceLock(tmp_path):
                pass
    with InstanceLock(tmp_path):
        pass


def test_live_server_and_shutdown(tmp_path):
    jobs = JobManager(LocalState(tmp_path / 'state'))
    server = LocalServer(create_app(job_manager=jobs), jobs)
    assert server.server.server_address[0] == '127.0.0.1'
    assert server.server.server_port > 0
    server.start()
    try:
        assert b'"ok"' in urlopen(server.url + '/api/health').read()
        assert b'File Organizer' in urlopen(server.url).read()
        assert urlopen(server.url + '/static/app.js').status == 200
    finally:
        server.close()
    server.close()
    assert not server.thread.is_alive()


def test_shutdown_waits_for_ongoing_operation(tmp_path):
    jobs = JobManager(LocalState(tmp_path))
    jobs._operation_lock.acquire()
    waiter = threading.Thread(target=jobs.wait_for_idle)
    waiter.start()
    time.sleep(.05)
    assert waiter.is_alive()
    jobs._operation_lock.release()
    waiter.join(2)
    assert not waiter.is_alive()


def test_real_files_preview_organize_history_undo(tmp_path):
    folder = tmp_path / 'files'
    folder.mkdir()
    (folder / 'sample.txt').write_text('safe temporary content')
    jobs = JobManager(LocalState(tmp_path / 'state'))
    preview = PreviewStore().create(str(folder))
    assert len(preview.plan_result.plans) == 1
    job = jobs.start(preview)
    jobs.wait_for_idle()
    assert job.status == 'completed'
    assert len(jobs.state.history()) == 1
    result = jobs.undo(job.job_id)
    assert result['success_count'] == 1
    assert (folder / 'sample.txt').read_text() == 'safe temporary content'


def test_launcher_window_and_cleanup(tmp_path):
    class Event:
        def __iadd__(self, handler):
            self.handler = handler
            return self
    class Window:
        class events:
            closing = Event()
        destroyed = threading.Event()
        def destroy(self):
            self.destroyed.set()
    class Webview:
        def create_window(self, title, url, **kwargs):
            self.url = url
            assert title.startswith('File Organizer')
            assert kwargs['width'] <= 1100 and kwargs['height'] <= 800
            assert kwargs['min_size'][0] <= kwargs['width'] and kwargs['min_size'][1] <= kwargs['height']
            return Window()
        def start(self, **kwargs):
            assert kwargs['gui'] == 'edgechromium'
            assert urlopen(self.url).status == 200
            assert Window.events.closing.handler() is False
            assert Window.destroyed.wait(5)
    run_desktop(Webview(), tmp_path)
    with InstanceLock(tmp_path):
        pass


def test_launcher_failure_releases_resources(tmp_path):
    class BrokenWebview:
        def create_window(self, *args, **kwargs):
            raise RuntimeError('window failed')
    with pytest.raises(RuntimeError):
        run_desktop(BrokenWebview(), tmp_path)
    with InstanceLock(tmp_path):
        pass
    assert not any(t.name == 'desktop-http' for t in threading.enumerate())


def test_frozen_app_serves_bundled_resources(monkeypatch, tmp_path):
    for name in ('templates', 'static'):
        shutil.copytree(resource_path(name), tmp_path / name)
    monkeypatch.setattr(sys, '_MEIPASS', str(tmp_path), raising=False)
    client = create_app(data_directory=tmp_path / 'state').test_client()
    assert client.get('/').status_code == 200
    assert client.get('/static/style.css').status_code == 200


def test_port_allocation_with_other_listener(tmp_path):
    with socket.socket() as occupied:
        occupied.bind(('127.0.0.1', 0))
        occupied.listen()
        jobs = JobManager(LocalState(tmp_path))
        server = LocalServer(create_app(job_manager=jobs), jobs)
        try:
            assert server.server.server_port != occupied.getsockname()[1]
        finally:
            server.close()


def test_instance_lock_across_processes(tmp_path):
    script = (
        'from desktop_app import InstanceLock, AlreadyRunning; import sys\n'
        'try:\n'
        ' with InstanceLock(sys.argv[1]): pass\n'
        'except AlreadyRunning: sys.exit(23)\n'
    )
    with InstanceLock(tmp_path):
        child = subprocess.run([sys.executable, '-c', script, str(tmp_path)],
                               cwd=resource_path('.'), capture_output=True)
        assert child.returncode == 23, child.stderr


def test_close_drains_inflight_request(tmp_path):
    entered = threading.Event()
    release = threading.Event()
    jobs = JobManager(LocalState(tmp_path))
    app = create_app(job_manager=jobs)
    @app.get('/slow-operation')
    def operation():
        entered.set()
        assert release.wait(5)
        return 'done'
    server = LocalServer(app, jobs)
    server.start()
    request_thread = threading.Thread(target=lambda: urlopen(server.url + '/slow-operation').read())
    request_thread.start()
    assert entered.wait(2)
    closer = threading.Thread(target=server.close)
    closer.start()
    time.sleep(.1)
    assert closer.is_alive()
    release.set()
    request_thread.join(5)
    closer.join(5)
    assert not closer.is_alive()


def test_window_uses_target_size_on_large_work_area():
    # 1920x1080 at 100%, taskbar 40px: full 1100x800, centred.
    assert fit_window((0, 0, 1920, 1040)) == {
        'width': 1100, 'height': 800, 'x': 410, 'y': 120, 'min_size': (800, 600)}


@pytest.mark.parametrize('work_area', [
    (0, 0, 1280, 672),    # 1280x720 at 150% (1920x1080 physical), taskbar 48px
    (0, 0, 1536, 816),    # 1920x1080 at 125%
    (0, 0, 1366, 728),    # 1366x768 at 100%
    (0, 48, 1280, 672),   # taskbar at the top
    (-1280, 0, 1280, 984),  # secondary monitor left of the primary
    (0, 0, 1024, 560),    # very small work area: minimum size must shrink too
])
def test_window_never_exceeds_work_area(work_area):
    left, top, width, height = work_area
    geometry = fit_window(work_area)
    assert left <= geometry['x'] and geometry['x'] + geometry['width'] <= left + width
    assert top <= geometry['y'] and geometry['y'] + geometry['height'] <= top + height
    assert geometry['width'] <= 1100 and geometry['height'] <= 800
    assert geometry['min_size'][0] <= geometry['width']
    assert geometry['min_size'][1] <= geometry['height']
    # Centred within one pixel.
    assert abs((geometry['x'] - left) - (left + width - geometry['x'] - geometry['width'])) <= 1


def test_window_on_1280x720_at_150_percent():
    geometry = fit_window((0, 0, 1280, 672))
    assert (geometry['width'], geometry['height']) == (1100, 640)
    assert geometry['y'] + geometry['height'] <= 672  # stays above the taskbar
    assert geometry['min_size'] == (800, 600)


def test_unknown_work_area_keeps_previous_defaults():
    assert fit_window(None) == {'width': 1100, 'height': 800, 'min_size': (800, 600)}


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows API')
def test_windows_work_area_is_readable():
    area = windows_work_area()
    assert area is not None
    assert area[2] > 0 and area[3] > 0
