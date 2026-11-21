"""A abertura deve reaproveitar só o servidor deste projeto e esperar prontidão."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket
import subprocess
import sys
import threading
from urllib.request import urlopen

import pytest

from osler import local_launcher as launcher


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


@pytest.fixture
def project(tmp_path):
    (tmp_path / 'app.py').write_text('import streamlit as st\nst.write("Ready")\n')
    return tmp_path


@pytest.fixture
def servers(monkeypatch):
    children = []
    original = launcher.subprocess.Popen
    def spawn(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(launcher.subprocess, 'Popen', spawn)
    yield children
    for child in children:
        if child.poll() is None:
            launcher._stop_child(child)


def test_ready_server_is_reused_without_a_second_process(project, servers):
    port = free_port()
    url = launcher.ensure_running(project, port=port, timeout=20)
    assert url == f'http://127.0.0.1:{port}/'
    with urlopen(url + '_stcore/health', timeout=2) as response:
        assert response.read() == b'ok'
    assert launcher.ensure_running(project, port=port, timeout=2) == url
    assert len(servers) == 1
    assert servers[0].poll() is None


def test_simultaneous_openings_start_one_server(project, servers):
    port = free_port()
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(launcher.ensure_running, project, port=port, timeout=20) for _ in range(2)]
        urls = [f.result() for f in futures]
    assert urls[0] == urls[1]
    assert len(servers) == 1


def test_other_project_on_the_port_is_not_reused_or_stopped(project, servers, tmp_path):
    other = tmp_path / 'other'
    other.mkdir()
    (other / 'app.py').write_text('import streamlit as st\nst.write("Other")\n')
    port = free_port()
    launcher.ensure_running(other, port=port, timeout=20)
    with pytest.raises(launcher.LaunchError, match='ocupada'):
        launcher.ensure_running(project, port=port, timeout=2)
    assert len(servers) == 1 and servers[0].poll() is None


def test_healthy_http_service_without_project_identity_is_not_opened(project):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'ok')
        def log_message(self, *_): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(launcher.LaunchError, match='ocupada'):
            launcher.ensure_running(project, port=server.server_port, timeout=2)
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_failed_child_reports_the_log_and_never_opens_browser(project, monkeypatch):
    process = subprocess.Popen([sys.executable, '-c', 'raise SystemExit(23)'])
    process.wait(timeout=5)
    monkeypatch.setattr(launcher, '_start_server', lambda *args: process)
    opened = []
    monkeypatch.setattr(launcher.webbrowser, 'open', lambda url: opened.append(url))
    with pytest.raises(launcher.LaunchError, match='server.log'):
        launcher.launch(project, port=free_port(), timeout=2)
    assert not opened


def test_timeout_stops_only_the_child_it_started(project, monkeypatch):
    process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    monkeypatch.setattr(launcher, '_start_server', lambda *args: process)
    try:
        with pytest.raises(launcher.LaunchError, match='server.log'):
            launcher.ensure_running(project, port=free_port(), timeout=.3)
        assert process.poll() is not None
    finally:
        if process.poll() is None: launcher._stop_child(process)


def test_browser_opens_only_after_matching_server_is_ready(project, servers, monkeypatch):
    seen = []
    def open_browser(url):
        with urlopen(url + '_stcore/health', timeout=2) as response:
            seen.append(response.read())
    monkeypatch.setattr(launcher.webbrowser, 'open', open_browser)
    launcher.launch(project, port=free_port(), timeout=20)
    assert seen == [b'ok']


@pytest.mark.skipif(sys.platform != 'win32', reason='Atalhos de encerramento do Windows')
def test_stop_closes_only_the_recorded_server(project, servers):
    launcher.ensure_running(project, port=free_port(), timeout=20)
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    try:
        launcher.stop(project)
        servers[0].wait(timeout=10)
        assert unrelated.poll() is None
        assert not (project / '.osler-runtime/server.json').exists()
    finally:
        launcher._stop_child(unrelated)


@pytest.mark.skipif(sys.platform != 'win32', reason='Identidade de processo do Windows')
def test_stop_rejects_a_reused_process_id(project, servers):
    import json
    launcher.ensure_running(project, port=free_port(), timeout=20)
    path = project / '.osler-runtime/server.json'
    record = json.loads(path.read_text())
    record['started'] -= 1
    path.write_text(json.dumps(record))
    with pytest.raises(launcher.LaunchError, match='mudou'):
        launcher.stop(project)
    assert servers[0].poll() is None


@pytest.mark.skipif(sys.platform != 'win32', reason='Identidade de processo do Windows')
def test_server_ownership_is_recorded_before_waiting_for_readiness(project, servers, monkeypatch):
    original = launcher._ready
    observed = []
    def ready(url, identity):
        if servers:
            assert (project / '.osler-runtime/server.json').is_file()
            observed.append(True)
        return original(url, identity)
    monkeypatch.setattr(launcher, '_ready', ready)
    launcher.ensure_running(project, port=free_port(), timeout=20)
    assert observed


def test_login_startup_prepares_server_without_opening_browser(project, servers, monkeypatch):
    port = free_port()
    original = launcher.ensure_running
    monkeypatch.setattr(launcher, '__file__', str(project / 'osler/local_launcher.py'))
    monkeypatch.setattr(sys, 'argv', ['osler', '--background'])
    monkeypatch.setattr(launcher, 'ensure_running', lambda root: original(root, port=port, timeout=20))
    opened = []
    monkeypatch.setattr(launcher.webbrowser, 'open', lambda url: opened.append(url))
    assert launcher.main() == 0
    assert len(servers) == 1 and servers[0].poll() is None
    assert not opened


def test_background_failure_without_console_is_logged(project, monkeypatch):
    monkeypatch.setattr(launcher, '__file__', str(project / 'osler/local_launcher.py'))
    monkeypatch.setattr(sys, 'argv', ['osler', '--background'])
    monkeypatch.setattr(sys, 'stderr', None)
    def fail(*args, **kwargs): raise launcher.LaunchError('Porta ocupada no teste')
    monkeypatch.setattr(launcher, 'ensure_running', fail)
    assert launcher.main() == 1
    assert 'Porta ocupada no teste' in (project / '.osler-runtime/launcher.log').read_text(encoding='utf-8')
