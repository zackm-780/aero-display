# Flight List Filtering + Radar Label Cleanup Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show airborne-only nearby flights with richer board data and cleaner radar labels while fixing logo rendering.

**Architecture:** Filter out ground traffic in backend state processing, keep board density and scroll behavior in frontend, and split radar symbol vs label visual orientation so arrows rotate but text remains upright. Use a robust logo fallback chain to avoid broken images.

**Tech Stack:** Python/FastAPI backend; vanilla JS/CSS frontend; Pytest.

---

### Task 1: Airborne filtering in backend

**Files:**
- Modify: `backend/app/flight_models.py`
- Modify: `backend/tests/test_filtering.py`

**Steps:**
1. Add failing test proving `on_ground=True` states are excluded from both board and radar lists.
2. Run: `venv/bin/pytest -q backend/tests/test_filtering.py` (expect FAIL first).
3. Implement minimal fix in `build_flight_lists` to skip ground states and preserve sorting/range behavior.
4. Re-run same test (expect PASS).

### Task 2: Board capacity/scroll + speed units + logo fallback

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `backend/tests/test_frontend_ui_contract.py`

**Steps:**
1. Add failing frontend contract tests for board max size (20) and logo fallback behavior.
2. Run: `venv/bin/pytest -q backend/tests/test_frontend_ui_contract.py` (expect FAIL first).
3. Update board constants and rendering to support up to 20 flights with vertical scrolling.
4. Convert velocity display from m/s to knots.
5. Add `<img onerror>` fallback behavior to show code badge when logo file is missing.
6. Re-run test (expect PASS).

### Task 3: Upright top-N radar labels with leader lines

**Files:**
- Modify: `frontend/app.js`
- Modify: `frontend/styles.css`
- Modify: `backend/tests/test_frontend_ui_contract.py`

**Steps:**
1. Add failing contract test for top-N radar label constant and leader-line class markers.
2. Run: `venv/bin/pytest -q backend/tests/test_frontend_ui_contract.py` (expect FAIL first).
3. Render plane arrow and label in separate transforms so text remains upright.
4. Show labels for closest N radar flights (default 12), with leader lines and simple offset strategy.
5. Ensure hover/select can still be extended without regression.
6. Re-run test (expect PASS).

### Task 4: End-to-end verification

**Files:**
- Verify: runtime UI via `http://localhost:8000/ui/`

**Steps:**
1. Run targeted tests:
   - `venv/bin/pytest -q backend/tests/test_filtering.py`
   - `venv/bin/pytest -q backend/tests/test_frontend_ui_contract.py`
2. Run broader suite if stable:
   - `venv/bin/pytest -q backend/tests`
3. Verify in browser: airborne-only board entries, vertical scroll with up to 20 flights, upright radar labels with leader lines, and no broken logo icons.
