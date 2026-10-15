"""Translate a Windows console break into cooperative runner cleanup."""
import signal
import sys
from arena.cli import main


def interrupt(signum, frame):
    raise KeyboardInterrupt


def run():
    signal.signal(signal.SIGTERM, interrupt)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, interrupt)
    try:
        return main()
    except KeyboardInterrupt:
        print("Exécution arrêtée. Les checkpoints conservés seront vérifiés à la reprise.", flush=True)
        return 130


if __name__ == "__main__":
    sys.exit(run())
