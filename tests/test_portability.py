"""Exercise native locks and subprocess cleanup on each CI operating system."""
import os
import subprocess
import sys
import unittest

from arena.core import ArenaError, ROOT, file_lock, scratch_directory
from arena.engine import OUTPUT_LIMIT, WorkerOutputLimit, stop_worker, wait_worker


class PortabilityTests(unittest.TestCase):
    def test_lock_excludes_other_process_and_releases_after_crash(self):
        with scratch_directory() as tmp:
            lock = tmp / "artifacts.lock"
            code = (
                "import sys, time\nfrom pathlib import Path\n"
                "from arena.core import ArenaError, file_lock\n"
                "try:\n"
                " with file_lock(Path(sys.argv[1])):\n"
                "  print('locked', flush=True)\n"
                "  time.sleep(60)\n"
                "except ArenaError:\n sys.exit(23)\n"
            )
            args = [sys.executable, "-c", code, str(lock)]
            with file_lock(lock):
                blocked = subprocess.run(args, cwd=ROOT, capture_output=True, timeout=10)
                self.assertEqual(blocked.returncode, 23, blocked.stderr)
            child = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                # Bound the readiness wait and close the pipe if startup fails.
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    ready = pool.submit(child.stdout.readline)
                    try:
                        self.assertEqual(ready.result(timeout=10).strip(), "locked")
                    except BaseException:
                        child.kill()
                        raise
                with self.assertRaises(ArenaError):
                    with file_lock(lock):
                        pass
            finally:
                child.kill()
                child.communicate(timeout=10)
            with file_lock(lock):
                pass

    def worker(self, code, work):
        return subprocess.Popen([sys.executable, "-c", code], cwd=work,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                start_new_session=os.name == "posix")

    def test_deadline_terminates_worker(self):
        with scratch_directory() as tmp:
            child = self.worker("import time; time.sleep(60)", tmp)
            try:
                with self.assertRaises(subprocess.TimeoutExpired):
                    wait_worker(child, tmp, 0.05)
            finally:
                stop_worker(child)
            self.assertIsNotNone(child.poll())

    def test_cleanup_stops_child_processes(self):
        import time
        with scratch_directory() as tmp:
            code = (
                "import subprocess, sys, time; from pathlib import Path; "
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
                "Path('child.pid.tmp').write_text(str(child.pid)); "
                "Path('child.pid.tmp').rename('child.pid'); time.sleep(60)"
            )
            parent = self.worker(code, tmp)
            child_pid = None
            try:
                deadline = time.monotonic() + 10
                while not (tmp / "child.pid").exists():
                    if time.monotonic() >= deadline or parent.poll() is not None:
                        self.fail("Worker did not create its child")
                    time.sleep(0.01)
                child_pid = int((tmp / "child.pid").read_text())
                stop_worker(parent)
                if os.name == "nt":
                    import ctypes
                    from ctypes import wintypes
                    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                    kernel.OpenProcess.restype = wintypes.HANDLE
                    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
                    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
                    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
                    handle = kernel.OpenProcess(0x1000, False, child_pid)
                    if handle:
                        try:
                            code = wintypes.DWORD()
                            self.assertTrue(kernel.GetExitCodeProcess(handle, ctypes.byref(code)))
                            self.assertNotEqual(code.value, 259, "Child process is still running")
                        finally:
                            kernel.CloseHandle(handle)
                elif sys.platform.startswith("linux"):
                    from pathlib import Path
                    state = Path(f"/proc/{child_pid}/stat")
                    if state.exists():
                        self.assertEqual(state.read_text().rsplit(")", 1)[1].split()[0], "Z")
            finally:
                if parent.poll() is None:
                    stop_worker(parent)
                if child_pid:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/PID", str(child_pid), "/F"],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                    else:
                        try:
                            os.kill(child_pid, 9)
                        except ProcessLookupError:
                            pass

    def test_output_limit_is_checked_even_after_exit(self):
        with scratch_directory() as tmp:
            # A sparse oversized file tests the real size check without generating log spam.
            with (tmp / "outcome.json").open("wb") as stream:
                stream.truncate(OUTPUT_LIMIT + 1)
            child = self.worker("pass", tmp)
            try:
                with self.assertRaises(WorkerOutputLimit):
                    wait_worker(child, tmp, 10)
            finally:
                stop_worker(child)

    def test_normal_worker_completes(self):
        with scratch_directory() as tmp:
            child = self.worker("pass", tmp)
            try:
                wait_worker(child, tmp, 10)
                self.assertEqual(child.returncode, 0)
            finally:
                if child.poll() is None:
                    stop_worker(child)
