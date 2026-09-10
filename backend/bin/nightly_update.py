#!/usr/bin/env python
"""Nightly update pipeline — run by cron on Wed/Thu/Fri evening.

Runs the full chain end to end. Any step that exits non-zero aborts the rest
and sends an alert email to GMAIL_USER (bundestag.im.o.ton@gmail.com).

Steps:
  1. bin/update_speeches.py        — fetch + embed new sessions, rebuild
                                     tops.json / abstimmungen.json, run the DIP
                                     cross-check (drucksache_verified), prewarm
                                     summaries + Drucksachen-Zusammenfassungen,
                                     upload everything to GCS
  2. gcloud run services update     — force a Cloud Run cold start so the warm
                                     instance drops its stale in-memory caches

The DIP cross-check runs inside step 1 (bin/update_speeches.py passes
verify_drucksachen=True) *before* the Drucksachen-Zusammenfassung prewarm, so a
brand-new document-backed TOP gets its summary on the same run. The /admin/update
endpoint runs the pipeline without the verify (it would run without the
machine-local overrides / DIP cache in Cloud Run).

Usage:
    uv run python bin/nightly_update.py
    uv run python bin/nightly_update.py --dry-run   # print the plan, run nothing
"""
import argparse
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

# Run from backend/ no matter what cron's working directory is.
BACKEND_DIR = Path(__file__).resolve().parent.parent
os.chdir(BACKEND_DIR)

from practicepreach.params import GMAIL_APP_PASSWORD, GMAIL_USER  # noqa: E402

GCLOUD = os.environ.get("GCLOUD_BIN") or "/opt/homebrew/bin/gcloud"
CLOUD_RUN_SERVICE = os.environ.get("CLOUD_RUN_SERVICE", "rag-backend")
CLOUD_RUN_REGION = os.environ.get("CLOUD_RUN_REGION", "europe-west10")
CLOUD_RUN_PROJECT = os.environ.get("CLOUD_RUN_PROJECT", "lw-speech-preach")

_EMAIL_OUTPUT_TAIL = 8000  # chars of the failing step's output to include in the alert


class StepError(RuntimeError):
    def __init__(self, label: str, returncode: int, output: str):
        super().__init__(f"step '{label}' exited {returncode}")
        self.label = label
        self.returncode = returncode
        self.output = output


def _steps() -> list[tuple[str, list[str]]]:
    py = sys.executable
    return [
        ("1/2 update_speeches", [py, "bin/update_speeches.py"]),
        (
            "2/2 Cloud Run cold start",
            [GCLOUD, "run", "services", "update", CLOUD_RUN_SERVICE,
             "--region", CLOUD_RUN_REGION, "--project", CLOUD_RUN_PROJECT],
        ),
    ]


def run_step(label: str, cmd: list[str]) -> None:
    print(f"\n=== {label} ===\n$ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    output = (proc.stdout or "")
    if proc.stderr:
        output += "\n[stderr]\n" + proc.stderr
    print(output, flush=True)
    if proc.returncode != 0:
        raise StepError(label, proc.returncode, output)


def send_alert(subject: str, body: str) -> None:
    if not (GMAIL_USER and GMAIL_APP_PASSWORD):
        print("No GMAIL_USER / GMAIL_APP_PASSWORD set — cannot send alert email.", file=sys.stderr, flush=True)
        return
    import smtplib
    from email.mime.text import MIMEText

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER
    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        print("Alert email sent.", flush=True)
    except Exception as exc:  # noqa: BLE001 — never let alerting mask the original error
        print(f"Alert email failed: {exc}", file=sys.stderr, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    parser.add_argument("--test-email", action="store_true", help="send a test alert email and exit")
    args = parser.parse_args()

    if args.test_email:
        send_alert(
            "Bundestag im O-Ton – Test der Fehler-Benachrichtigung",
            "Dies ist eine Testnachricht von bin/nightly_update.py --test-email.\n"
            "Wenn du das liest, funktioniert das Alerting.\n",
        )
        return 0

    steps = _steps()
    started = datetime.now()
    print(f"===== nightly_update {started:%Y-%m-%d %H:%M:%S} =====", flush=True)

    if args.dry_run:
        for label, cmd in steps:
            print(f"  {label}: {' '.join(cmd)}")
        print(f"  on failure: email GMAIL_USER ({GMAIL_USER or 'unset'})")
        return 0

    try:
        for label, cmd in steps:
            run_step(label, cmd)
    except StepError as exc:
        print(f"\nFAILED at {exc.label}", file=sys.stderr, flush=True)
        body = (
            "Der nächtliche Update-Lauf ist fehlgeschlagen.\n\n"
            f"Fehlgeschlagener Schritt: {exc.label} (exit {exc.returncode})\n"
            f"Start: {started:%Y-%m-%d %H:%M:%S}\n"
            f"Ende:  {datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            "Ausgabe des Schritts (gekürzt):\n"
            "----------------------------------------\n"
            f"{exc.output[-_EMAIL_OUTPUT_TAIL:]}\n"
            "----------------------------------------\n\n"
            "Vollständiges Log: /tmp/preach_update.log auf dem Update-Rechner.\n"
        )
        send_alert("Bundestag im O-Ton – nächtlicher Update-Lauf fehlgeschlagen", body)
        return 1
    except Exception:  # noqa: BLE001
        err = traceback.format_exc()
        print(err, file=sys.stderr, flush=True)
        send_alert(
            "Bundestag im O-Ton – nächtlicher Update-Lauf abgestürzt",
            f"Unerwarteter Fehler im nightly_update.py-Wrapper.\n\n{err}\n"
            "Vollständiges Log: /tmp/preach_update.log auf dem Update-Rechner.\n",
        )
        return 1

    elapsed = int((datetime.now() - started).total_seconds())
    print(f"\nAlle Schritte OK in {elapsed}s.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
