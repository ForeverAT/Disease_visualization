import argparse
import time
from datetime import datetime

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from pipeline import run_pipeline

CSV_PATH = "data/observations.csv"
OUTPUT_PATH = "output/spread.geojson"
DEBOUNCE_SECONDS = 1.0


class CsvChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self._last_trigger = 0.0

    def on_modified(self, event):
        if not event.src_path.endswith("observations.csv"):
            return
        now = time.time()
        if now - self._last_trigger < DEBOUNCE_SECONDS:
            return
        self._last_trigger = now
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Change detected — running pipeline...")
        try:
            run_pipeline(CSV_PATH, OUTPUT_PATH)
        except Exception as exc:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Pipeline error: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Disease Spread Visualizer watcher")
    parser.add_argument(
        "--once", action="store_true", help="Run pipeline once and exit (no watching)"
    )
    args = parser.parse_args()

    if args.once:
        run_pipeline(CSV_PATH, OUTPUT_PATH)
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting — initial pipeline run...")
    try:
        run_pipeline(CSV_PATH, OUTPUT_PATH)
    except Exception as exc:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Initial pipeline error: {exc}")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Watching {CSV_PATH} for changes. Ctrl+C to stop.")
    handler = CsvChangeHandler()
    observer = Observer()
    observer.schedule(handler, path="data/", recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()


if __name__ == "__main__":
    main()
