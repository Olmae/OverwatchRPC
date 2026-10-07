# OWRPC Desktop Implementation Plan

**Goal:** Ship a Windows tray companion with dependable manual Rich Presence and
optional local OCR, publish source and a Windows beta build in Olmae/OverwatchRPC.

**Architecture:** Standard Python/Tkinter UI, isolated Discord/OCR worker, queued
UI updates. Keep platform integration separate from testable state and storage.

**Tech stack:** Python 3.12, Tkinter, pystray, Pillow, pypresence, psutil,
pytesseract; PyInstaller and GitHub Actions for Windows packaging.

**Spec:** `docs/design.md`.

## Constraints and review focus

- Discord unavailable must never prevent startup or freeze the UI.
- Corrupt settings must be recoverable without losing the original file.
- Unsupported platforms and tray failure must leave a working exit path.
- OCR cannot invent a hero/map or keep pending observations across manual changes.
- Match timers must reset between games and must not reset on every polling tick.

## Tasks

1. [x] Write/run failing unittest cases for model, storage, matching and RPC lifecycle.
2. [x] Implement validated settings, catalogs, payloads, atomic storage and worker.
3. [x] Implement Windows integration, optional calibrated OCR and Tkinter/tray UI.
4. [x] Add packaging, CI, English README, diagnostics and Windows acceptance checklist.
5. [ ] Run unit tests, dependency checks and available UI verification; fix findings.
6. [ ] Commit/push to user fork, verify CI, publish beta release if build succeeds.
