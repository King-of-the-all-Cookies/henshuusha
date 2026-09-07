"""Background workers and non-blocking Windows notifications."""
import logging
import threading
import traceback

from PyQt6.QtCore import QThread, QObject, pyqtSignal


class WorkerSignals(QObject):
    result = pyqtSignal(object)
    finished = pyqtSignal()
    error = pyqtSignal(tuple)


class WorkerThread(QThread):
    """Runs an arbitrary callable in a background thread with Qt signals.

    Signals:
        result: emitted with the return value on success.
        error:  emitted with (exception, traceback string) on failure.
        finished: always emitted once the callable has returned/raised.
    """

    def __init__(self, function, *args):
        super().__init__()
        self.function = function
        self.args = args
        self.signals = WorkerSignals()

    def run(self):
        name = getattr(self.function, "__name__", repr(self.function))
        try:
            logging.info("Worker started: %s", name)
            result = self.function(*self.args)
            self.signals.result.emit(result)
        except Exception as e:
            traceback_str = traceback.format_exc()
            logging.error(f"Worker error in {name}: {e}\n{traceback_str}")
            self.signals.error.emit((e, traceback_str))
        finally:
            self.signals.finished.emit()


def notify(title: str, message: str) -> None:
    """Show a Windows toast notification without blocking the UI.

    win11toast.toast() can block until the notification is dismissed,
    so it is executed in a daemon thread.
    """

    def _show():
        try:
            from win11toast import toast
            toast(title, message)
        except Exception as e:
            logging.error(f"Toast notification failed: {e}")

    threading.Thread(target=_show, daemon=True).start()