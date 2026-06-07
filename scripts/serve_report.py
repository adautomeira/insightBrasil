#!/usr/bin/env python3
"""Serve the generated report.html over localhost — zero external dependencies.

Regenerates the report (so it's always current with the local data/ files),
then serves the project root with Python's stdlib http.server and opens it
in the default browser.

Usage: python3 serve_report.py [port]   (default port: 8000)
"""

import sys
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import generate_report

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_NAME = generate_report.DEFAULT_OUTPUT.name


class ReportHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PROJECT_ROOT), **kwargs)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000

    generate_report.build_report_to(generate_report.DEFAULT_OUTPUT)
    url = f"http://localhost:{port}/{REPORT_NAME}"

    server = HTTPServer(("localhost", port), ReportHandler)
    print(f"Serving {REPORT_NAME} at {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        server.shutdown()


if __name__ == "__main__":
    main()
