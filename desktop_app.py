"""Dedicated Windows window; no external browser or development server."""
from __future__ import annotations

import ctypes
import logging
import os
from pathlib import Path
from threading import Event, Thread

from werkzeug.serving import make_server

from app_config import APP_NAME, VERSION, resource_path, user_data_directory
from local_state import LocalState
from organizer_service import JobManager
from web_app import create_app


WINDOW_SIZE = (1100, 800)
MIN_WINDOW_SIZE = (800, 600)
WINDOW_MARGIN = 16


class AlreadyRunning(RuntimeError):
    pass


def fit_window(work_area, size=WINDOW_SIZE, min_size=MIN_WINDOW_SIZE, margin=WINDOW_MARGIN):
    """Size/position (logical px) that fits inside the work area, centred.

    work_area is (left, top, width, height) in logical px, or None when unknown.
    """
    if not work_area:
        return {"width": size[0], "height": size[1], "min_size": min_size}
    left, top, work_width, work_height = work_area
    width = max(1, min(size[0], work_width - 2 * margin))
    height = max(1, min(size[1], work_height - 2 * margin))
    return {
        "width": width,
        "height": height,
        "x": left + (work_width - width) // 2,
        "y": top + (work_height - height) // 2,
        # A minimum larger than the screen would push the window under the taskbar.
        "min_size": (min(min_size[0], width), min(min_size[1], height)),
    }


def windows_work_area():
    """Work area (excluding the taskbar) of the monitor under the cursor, in logical px.

    pywebview 6 (WinForms) makes the process system-DPI-aware and multiplies the
    requested size/position by GetDpiForWindow()/96. To use the same coordinate
    space, read the work area as a system-DPI-aware thread and divide by the
    system DPI. Returns None when it cannot be determined (caller keeps defaults).
    """
    if os.name != "nt":
        return None
    from ctypes import wintypes

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]

    user32 = ctypes.windll.user32
    previous = None
    try:
        set_context = getattr(user32, "SetThreadDpiAwarenessContext", None)
        if set_context is not None:  # Windows 10 1607+
            set_context.restype = ctypes.c_void_p
            set_context.argtypes = [ctypes.c_void_p]
            previous = set_context(ctypes.c_void_p(-2))  # DPI_AWARENESS_CONTEXT_SYSTEM_AWARE
        point = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(point))
        user32.MonitorFromPoint.restype = ctypes.c_void_p
        user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
        monitor = user32.MonitorFromPoint(point, 1)  # MONITOR_DEFAULTTOPRIMARY
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
        if not monitor or not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            return None
        # Without a system-aware thread the rectangle is already in 96-DPI units.
        dpi = user32.GetDpiForSystem() if previous else 96
        scale = (dpi or 96) / 96
        work = info.rcWork
        area = (int(work.left / scale), int(work.top / scale),
                int((work.right - work.left) / scale), int((work.bottom - work.top) / scale))
        return area if area[2] > 0 and area[3] > 0 else None
    except Exception:
        logging.exception("Could not read the Windows work area")
        return None
    finally:
        if previous:
            user32.SetThreadDpiAwarenessContext(ctypes.c_void_p(previous))


class InstanceLock:
    """OS byte lock is released even after a crash; never delete the lock file."""
    def __init__(self, directory):
        self.path = Path(directory) / "desktop.lock"
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = self.path.open("a+b")
        self.file.seek(0, 2)
        if self.file.tell() == 0:
            self.file.write(b"0")
            self.file.flush()
        self.file.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.file.close()
            self.file = None
            raise AlreadyRunning("File Organizer はすでに起動しています。") from error
        return self

    def __exit__(self, *args):
        if self.file:
            self.file.close()
            self.file = None


class LocalServer:
    """Bind port 0 directly: no port-probe/rebind race. Drain active requests."""
    def __init__(self, app, jobs):
        self.jobs = jobs
        self.server = make_server("127.0.0.1", 0, app, threaded=True)
        self.server.daemon_threads = False
        self.server.block_on_close = True
        self.thread = Thread(target=self.server.serve_forever, name="desktop-http")
        self.started = False
        self.closed = False

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_port}"

    def start(self):
        self.thread.start()
        self.started = True

    def close(self):
        if self.closed:
            return
        if self.started:
            self.server.shutdown()
            self.thread.join()
        self.server.server_close()  # Wait for synchronous Undo / request handlers.
        self.jobs.wait_for_idle()   # Wait for journaled background organization.
        self.closed = True


def run_desktop(webview, directory=None):
    directory = Path(directory) if directory is not None else user_data_directory()
    with InstanceLock(directory):
        jobs = JobManager(LocalState(directory))
        window = None

        def pick_folder():
            selected = window.create_file_dialog(webview.FileDialog.FOLDER)
            return selected[0] if selected else None

        server = LocalServer(create_app(job_manager=jobs, folder_picker=pick_folder), jobs)
        closing = Event()
        drained = Event()

        def on_closing():
            if drained.is_set():
                return None
            if not closing.is_set():
                closing.set()

                def finish():
                    server.close()
                    drained.set()
                    window.destroy()

                Thread(target=finish, name="desktop-shutdown").start()
            # Keep the GUI message loop alive for pending native dialogs.
            return False

        try:
            server.start()
            geometry = fit_window(windows_work_area())
            logging.info("Window geometry: %s", geometry)
            window = webview.create_window(f"{APP_NAME} {VERSION}", server.url, **geometry)
            window.events.closing += on_closing
            icon = resource_path("icons/app.ico")
            webview.start(gui="edgechromium", debug=False,
                          icon=str(icon) if icon.is_file() else None)
        finally:
            server.close()


def main():
    directory = user_data_directory()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=directory / "desktop.log", encoding="utf-8",
                            level=logging.INFO)
        import webview
        run_desktop(webview, directory)
    except Exception as error:
        logging.exception("Desktop startup failed")
        if os.name == "nt":
            ctypes.windll.user32.MessageBoxW(None, str(error), APP_NAME, 0x10)
        else:
            raise


if __name__ == "__main__":
    main()
