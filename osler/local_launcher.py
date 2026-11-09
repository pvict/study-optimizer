"""Abre o app local quando pronto; aberturas repetidas reutilizam o servidor."""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener
import webbrowser


class LaunchError(RuntimeError):
    pass


@contextmanager
def _startup_lock(path, deadline):
    """Trava nativa liberada pelo sistema mesmo se o lançador for interrompido."""
    with path.open('a+b') as handle:
        handle.seek(0, 2)
        if not handle.tell():
            handle.write(b'0'); handle.flush()
        locked = False
        while not locked:
            handle.seek(0)
            try:
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                locked = True
            except OSError:
                if time.monotonic() >= deadline:
                    raise LaunchError('Outra abertura ainda está em andamento. Aguarde e tente novamente.')
                time.sleep(.1)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_UN)


def _ready(url, identity):
    # Proxies do ambiente não devem interceptar uma conexão com o próprio PC.
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(url + '_stcore/health', timeout=.5) as response:
            if response.status != 200 or response.read(64) != b'ok': return False
        with opener.open(url + 'app/static/osler-instance.txt', timeout=.5) as response:
            return response.status == 200 and response.read(128).decode('ascii') == identity
    except (OSError, ValueError, UnicodeError):
        return False


def _listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.25): return True
    except OSError:
        return False


def _start_server(root, port, log_path):
    # Só rotacionar antes de iniciar; o processo ativo mantém seu próprio log.
    if log_path.exists() and log_path.stat().st_size > 1024 * 1024:
        log_path.replace(log_path.with_suffix('.previous.log'))
    with log_path.open('ab', buffering=0) as log:
        return subprocess.Popen(
            [sys.executable, '-m', 'streamlit', 'run', str(root / 'app.py'),
             '--server.address', '127.0.0.1', '--server.port', str(port),
             '--server.headless', 'true', '--server.enableStaticServing', 'true',
             '--browser.serverAddress', '127.0.0.1', '--browser.gatherUsageStats', 'false'],
            cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            close_fds=True)


def _stop_child(process):
    if process.poll() is not None: return
    if os.name == 'nt':
        # O executável da venv pode criar um filho. Apenas esta árvore recém-criada.
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdin=subprocess.DEVNULL, capture_output=True, check=False,
                       creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        process.terminate()
    process.wait(timeout=10)


@contextmanager
def _process_identity(pid):
    """Identidade de geração do PID no Windows; não confundir um PID reutilizado."""
    if os.name != 'nt':
        raise LaunchError('O encerramento pelo atalho é disponível no Windows.')
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        if ctypes.get_last_error() == 87:
            yield None  # PID já não existe.
            return
        raise LaunchError('Não foi possível verificar a identidade do processo do app.')
    try:
        values = [wintypes.FILETIME() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *[ctypes.byref(value) for value in values]):
            raise LaunchError('Não foi possível verificar a identidade do processo do app.')
        yield values[0].dwHighDateTime << 32 | values[0].dwLowDateTime
    finally:
        kernel.CloseHandle(handle)


def ensure_running(root, *, port=8501, timeout=45):
    root = Path(root).resolve()
    if not (root / 'app.py').is_file():
        raise LaunchError('Aplicativo não encontrado nesta pasta.')
    if type(port) is not int or not 1 <= port <= 65535:
        raise LaunchError('Porta local inválida.')
    runtime = root / '.osler-runtime'
    runtime.mkdir(exist_ok=True)
    deadline = time.monotonic() + timeout
    url = f'http://127.0.0.1:{port}/'
    identity = hashlib.sha256(os.path.normcase(str(root)).encode('utf-8')).hexdigest()
    with _startup_lock(runtime / 'startup.lock', deadline):
        static = root / 'static'
        static.mkdir(exist_ok=True)
        marker = static / 'osler-instance.txt'
        # Fingerprint da pasta, sem expor caminhos ou dados pessoais no endpoint.
        if not marker.exists() or marker.read_text(encoding='ascii') != identity:
            marker.write_text(identity, encoding='ascii')
        if _ready(url, identity): return url
        if _listening(port):
            raise LaunchError(f'A porta {port} está ocupada por outro serviço ou por um app ainda iniciando. '
                              'Nenhum processo foi encerrado.')
        log_path = runtime / 'server.log'
        process = _start_server(root, port, log_path)
        try:
            if os.name == 'nt':
                with _process_identity(process.pid) as started:
                    if started is None:
                        raise LaunchError(f'O servidor não iniciou. Detalhes em {log_path}')
                    record = {'pid': process.pid, 'started': started, 'identity': identity}
                temporary_record = runtime / 'server.pending.json'
                temporary_record.write_text(json.dumps(record), encoding='utf-8')
                temporary_record.replace(runtime / 'server.json')
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise LaunchError(f'O servidor não iniciou. Detalhes em {log_path}')
                if _ready(url, identity): return url
                time.sleep(.15)
            raise LaunchError(f'A abertura excedeu o tempo de espera. Detalhes em {log_path}')
        except BaseException:
            _stop_child(process)
            raise


def launch(root, *, port=8501, timeout=45):
    url = ensure_running(root, port=port, timeout=timeout)
    if not webbrowser.open(url):
        print(f'App pronto. Abra {url}')
    return url


def stop(root):
    root = Path(root).resolve()
    runtime = root / '.osler-runtime'
    if not runtime.exists(): return
    with _startup_lock(runtime / 'startup.lock', time.monotonic() + 45):
        record_path = runtime / 'server.json'
        if not record_path.exists():
            raise LaunchError('Não há servidor iniciado por este atalho. Se iniciou pelo terminal, use Ctrl+C nele.')
        try:
            record = json.loads(record_path.read_text(encoding='utf-8'))
            pid = record['pid']; started = record['started']
            identity = hashlib.sha256(os.path.normcase(str(root)).encode('utf-8')).hexdigest()
            if type(pid) is not int or pid <= 0 or type(started) is not int or record['identity'] != identity:
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise LaunchError('Registro do servidor inválido. Nenhum processo foi encerrado.') from None
        # Manter o handle verificado aberto até concluir: a identidade não pode
        # ser liberada e o PID reutilizado entre a conferência e o encerramento.
        with _process_identity(pid) as actual:
            if actual is not None and actual != started:
                raise LaunchError('O processo registrado já mudou. Nenhum processo foi encerrado.')
            if actual is not None:
                result = subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                                        creationflags=subprocess.CREATE_NO_WINDOW, check=False)
                if result.returncode:
                    raise LaunchError('Não foi possível encerrar o servidor. Tente novamente.')
        record_path.unlink()


def main():
    root = Path(__file__).resolve().parents[1]
    background = sys.argv[1:] == ['--background']
    try:
        if background:
            ensure_running(root)
        elif sys.argv[1:] == ['--stop']:
            stop(root)
            print('Osler encerrado.')
        elif sys.argv[1:]:
            raise LaunchError('Use iniciar.bat para abrir ou encerrar.bat para encerrar.')
        else:
            launch(root)
    except (LaunchError, OSError) as exc:
        message = f'Não foi possível concluir a ação: {exc}'
        try:
            folder = root / '.osler-runtime'
            folder.mkdir(exist_ok=True)
            log = folder / 'launcher.log'
            if log.exists() and log.stat().st_size > 262144:
                log.replace(log.with_suffix('.previous.log'))
            with log.open('a', encoding='utf-8') as output:
                output.write(f'{datetime.now().isoformat(timespec="seconds")} {message}\n')
        except OSError:
            pass  # Ainda apresentar a mensagem quando não é possível gravar.
        if sys.stderr is not None:
            print(message, file=sys.stderr)
        elif not background and os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'Osler', 0x10)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
