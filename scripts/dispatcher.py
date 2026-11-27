#!/usr/bin/env python3
"""
TASK-008.1 Dispatcher — Autonomous task queue dispatcher for Cloud-Native Stack reconciliation.

Reads pending tasks from the file-based queue, checks dependencies,
delegates implementation to workers, validates results, and updates task state.

Usage:
    python3 dispatcher.py [--once] [--max-tasks N]

Without --once, runs continuously until no eligible tasks remain.
"""

import os
import re
import shutil
import subprocess
import sys
import time
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Configuration
BASE_DIR = Path("/workspace/release-artifacts/TASK-008.0-persistent-runtime")
QUEUE_DIR = BASE_DIR / "tasks"
PENDING_DIR = QUEUE_DIR / "pending"
IN_PROGRESS_DIR = QUEUE_DIR / "in-progress"
COMPLETED_DIR = QUEUE_DIR / "completed"
BLOCKED_DIR = QUEUE_DIR / "blocked"
LOGS_DIR = BASE_DIR / "dispatcher-logs"
REPO_DIR = Path("/workspace/project/github/public-repository/cloud-native-guide")
INTEGRATION_BRANCH = "integration/reconcile-remote-content"
MAX_CONCURRENT = 5
MAX_RUNTIME_SECONDS = 300

# Ensure directories exist
for d in [PENDING_DIR, IN_PROGRESS_DIR, COMPLETED_DIR, BLOCKED_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def log(message):
    """Write a timestamped log message."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts}] {message}", flush=True)
    # Also write to dispatcher log
    log_file = LOGS_DIR / "dispatcher.log"
    with open(log_file, "a") as f:
        f.write(f"[{ts}] {message}\n")


def load_task(task_file):
    """Load a task file and parse its fields."""
    task = {
        "id": None,
        "title": None,
        "scope": None,
        "source": None,
        "target": None,
        "deliverables": None,
        "acceptance_criteria": [],
        "validation_commands": [],
        "completion_condition": None,
        "dependencies": [],
        "priority": 5,
        "assignee": "Hermes-Worker",
        "status": "pending",
        "created_at": None,
        "attempt_count": 0,
        "execution_history": [],
        "file": task_file,
    }
    
    try:
        content = task_file.read_text()
    except Exception as e:
        log(f"ERROR reading {task_file}: {e}")
        return None
    
    # Parse task ID from filename
    task["id"] = task_file.stem
    
    # Parse fields from content
    for line in content.split("\n"):
        line_stripped = line.strip()
        if line_stripped.startswith("**Scope:**"):
            task["scope"] = line_stripped.replace("**Scope:**", "").strip()
        elif line_stripped.startswith("**Source:**"):
            task["source"] = line_stripped.replace("**Source:**", "").strip()
        elif line_stripped.startswith("**Target:**"):
            task["target"] = line_stripped.replace("**Target:**", "").strip()
        elif line_stripped.startswith("**Dependencies:**"):
            deps_str = line_stripped.replace("**Dependencies:**", "").strip()
            if deps_str and deps_str != "None":
                task["dependencies"] = [d.strip().split()[0] for d in deps_str.split(",")]
        elif line_stripped.startswith("**Priority:**"):
            try:
                task["priority"] = int(line_stripped.replace("**Priority:**", "").strip())
            except ValueError:
                pass
        elif line_stripped.startswith("**Assignee:**"):
            task["assignee"] = line_stripped.replace("**Assignee:**", "").strip()
        elif line_stripped.startswith("**Status:**"):
            task["status"] = line_stripped.replace("**Status:**", "").strip()
        elif line_stripped.startswith("**Block reason:**"):
            task["block_reason"] = line_stripped.replace("**Block reason:**", "").strip()
    
    return task


def check_dependencies(task, completed_ids):
    """Check if all dependencies of a task are satisfied."""
    for dep in task["dependencies"]:
        if dep not in completed_ids:
            return False, dep
    return True, None


def get_completed_ids():
    """Get set of completed task IDs."""
    completed = set()
    if COMPLETED_DIR.exists():
        for f in COMPLETED_DIR.iterdir():
            if f.is_file() and f.suffix == ".md":
                completed.add(f.stem)
    return completed


def get_blocked_ids():
    """Get set of blocked task IDs."""
    blocked = set()
    if BLOCKED_DIR.exists():
        for f in BLOCKED_DIR.iterdir():
            if f.is_file() and f.suffix == ".md":
                blocked.add(f.stem)
    return blocked


def select_eligible_tasks(max_tasks=MAX_CONCURRENT):
    """Select eligible pending tasks whose dependencies are satisfied."""
    completed_ids = get_completed_ids()
    blocked_ids = get_blocked_ids()
    
    pending_tasks = []
    for f in sorted(PENDING_DIR.iterdir()):
        if f.is_file() and f.suffix == ".md":
            task = load_task(f)
            if task and task["status"] == "pending":
                pending_tasks.append((task, f))
    
    # Sort by priority (descending), then by creation order
    pending_tasks.sort(key=lambda x: -x[0]["priority"])
    
    eligible = []
    for task, f in pending_tasks:
        if len(eligible) >= max_tasks:
            break
        if task["id"] in blocked_ids:
            continue
        deps_ok, missing_dep = check_dependencies(task, completed_ids)
        if deps_ok:
            eligible.append((task, f))
    
    return eligible


def move_task(filename, from_dir, to_dir):
    """Move a task file from one directory to another."""
    src = from_dir / filename
    dst = to_dir / filename
    if src.exists():
        shutil.move(str(src), str(dst))
        log(f"Moved {filename}: {from_dir.name} -> {to_dir.name}")
        return True
    return False


def update_task_status(task_file, new_status, to_dir=None):
    """Update a task's status field and move it to the appropriate directory."""
    content = task_file.read_text()
    
    # Update status field
    lines = content.split("\n")
    new_lines = []
    for line in lines:
        if line.strip().startswith("**Status:**"):
            new_lines.append(f"**Status:** {new_status}")
        else:
            new_lines.append(line)
    
    task_file.write_text("\n".join(new_lines))
    
    # Move file if target directory specified
    if to_dir:
        current_dir = task_file.parent
        if current_dir != to_dir:
            move_task(task_file.name, current_dir, to_dir)


def validate_file_copy(worktree_dir, relative_path):
    """Validate a copied file: git diff --check, structure, etc."""
    results = {}
    
    # Ensure relative_path is a Path
    if not isinstance(relative_path, Path):
        relative_path = Path(relative_path)
    
    # Check file exists
    full_path = worktree_dir / relative_path
    results["file_exists"] = full_path.exists()
    
    if not full_path.exists():
        results["error"] = "File does not exist"
        return results
    
    # git diff --check
    try:
        result = subprocess.run(
            ["git", "diff", "--check"],
            cwd=str(worktree_dir),
            capture_output=True, text=True, timeout=30
        )
        results["git_diff_check"] = result.returncode == 0
        results["git_diff_check_output"] = result.stdout.strip()
    except Exception as e:
        results["git_diff_check"] = False
        results["git_diff_check_error"] = str(e)
    
    # Line count
    results["line_count"] = len(full_path.read_text(errors="replace").split("\n"))
    
    # Check for basic Markdown structure (for .md files)
    if relative_path.suffix == ".md":
        text = full_path.read_text(errors="replace")
        results["has_headers"] = bool(re.search(r"^#+\s", text, re.MULTILINE))
        results["header_count"] = len(re.findall(r"^#+\s", text, re.MULTILINE))
    
    # Check for Python syntax (for .py files)
    if relative_path.suffix == ".py":
        try:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(full_path)],
                capture_output=True, text=True, timeout=30
            )
            results["python_syntax"] = result.returncode == 0
            results["python_syntax_error"] = result.stderr.strip()
        except Exception as e:
            results["python_syntax"] = False
            results["python_syntax_error"] = str(e)
    
    return results


def copy_file_from_integration(worktree_dir, source_ref):
    """Copy a file from the integration branch into the worktree.
    
    source_ref can be just a file path or "branch @ sha file_path".
    """
    try:
        # Parse file path from source_ref (may include "branch @ sha prefix")
        parts = source_ref.strip().split()
        # The file path is typically the last part
        relative_path = parts[-1]
        
        full_path = worktree_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = subprocess.run(
            ["git", "show", f"{INTEGRATION_BRANCH}:{relative_path}"],
            cwd=str(REPO_DIR),
            capture_output=True, text=True, timeout=30
        )
        
        if result.returncode != 0:
            return False, f"git show failed: {result.stderr.strip()}"
        
        full_path.write_text(result.stdout)
        
        return True, None
    except Exception as e:
        return False, str(e)


def execute_task(task, task_file):
    """Execute a single task: copy file, validate, move to completed."""
    task_id = task["id"]
    log(f"Executing task {task_id}: {task['title']}")
    
    # Determine relative path from task scope or source
    # Try to extract the file path from scope
    relative_path = None
    if task["scope"]:
        # Look for file path patterns in scope (e.g., "Copy .gitignore from...")
        match = re.search(r'Copy\s+([\w\-\./]+\.\w+)\s+from', task["scope"])
        if match:
            relative_path = match.group(1)
        else:
            # Try any file-like pattern
            match = re.search(r'([\w\-\./]+\.\w+)', task["scope"])
            if match:
                relative_path = match.group(1)
    
    if not relative_path and task["source"]:
        # Source may be "branch @ sha file_path" — take last part
        parts = task["source"].strip().split()
        relative_path = parts[-1]
    
    if not relative_path:
        log(f"ERROR: Cannot determine file path for task {task_id}")
        update_task_status(task_file, "failed", IN_PROGRESS_DIR)
        return False
    
    # Determine worktree — use the latest phase worktree
    # Phase 7 and 8 worktrees exist but are uncommitted
    # For new tasks, create a new phase worktree or use existing
    worktree_dir = None
    
    # Check if there's an existing uncommitted worktree
    for pt in ["cloud-native-guide.phase7", "cloud-native-guide.phase8"]:
        pt_path = REPO_DIR.parent / pt
        if pt_path.exists():
            # Check if it has uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(pt_path),
                capture_output=True, text=True
            )
            if result.stdout.strip():
                worktree_dir = pt_path
                log(f"Using existing worktree {pt} with uncommitted changes")
                break
    
    if not worktree_dir:
        # Create a new Phase 9 worktree from latest commit (51da564)
        worktree_name = "cloud-native-guide.phase9"
        worktree_path = REPO_DIR.parent / worktree_name
        if not worktree_path.exists():
            result = subprocess.run(
                ["git", "worktree", "add", "-b", "task-008.1-p09-content",
                 str(worktree_path), "51da5642c5b743f9de3914f67da98f1de79cba5c"],
                cwd=str(REPO_DIR),
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                log(f"ERROR creating worktree: {result.stderr.strip()}")
                update_task_status(task_file, "failed", IN_PROGRESS_DIR)
                return False
        worktree_dir = worktree_path
        log(f"Created new worktree {worktree_name}")
    
    # Copy file from integration branch
    success, error = copy_file_from_integration(worktree_dir, relative_path)
    if not success:
        log(f"ERROR copying {relative_path}: {error}")
        update_task_status(task_file, "failed", IN_PROGRESS_DIR)
        return False
    
    log(f"Copied {relative_path} to {worktree_dir.name}")
    
    # Validate
    validation = validate_file_copy(worktree_dir, relative_path)
    
    all_valid = True
    if not validation.get("file_exists"):
        log(f"ERROR: File {relative_path} does not exist after copy")
        all_valid = False
    if not validation.get("git_diff_check"):
        log(f"ERROR: git diff --check failed for {relative_path}")
        all_valid = False
    if validation.get("python_syntax") is False:
        log(f"ERROR: Python syntax check failed for {relative_path}")
        all_valid = False
    
    if all_valid:
        log(f"Task {task_id} validated successfully")
        update_task_status(task_file, "completed", COMPLETED_DIR)
        return True
    else:
        log(f"Task {task_id} validation failed: {validation}")
        update_task_status(task_file, "failed", IN_PROGRESS_DIR)
        return False


def run_dispatcher(max_tasks=None, once=False):
    """Run the dispatcher loop."""
    log("=== Dispatcher starting ===")
    
    task_count = 0
    max_tasks = max_tasks or float('inf')
    
    while task_count < max_tasks:
        eligible = select_eligible_tasks(max_tasks=MAX_CONCURRENT)
        
        if not eligible:
            log("No eligible tasks remaining")
            break
        
        log(f"Selected {len(eligible)} eligible tasks")
        
        for task, task_file in eligible:
            if task_count >= max_tasks:
                break

            # Move to in-progress
            move_task(task_file.name, PENDING_DIR, IN_PROGRESS_DIR)
            # Update task_file to point to new location
            task_file = IN_PROGRESS_DIR / task_file.name
            update_task_status(task_file, "in-progress", None)
            
            # Execute
            success = execute_task(task, task_file)
            
            task_count += 1
            
            if once:
                break
        
        if once:
            break
    
    log(f"=== Dispatcher finished: {task_count} tasks executed ===")
    return task_count


if __name__ == "__main__":
    once = "--once" in sys.argv
    max_tasks = None
    for i, arg in enumerate(sys.argv):
        if arg == "--max-tasks" and i + 1 < len(sys.argv):
            try:
                max_tasks = int(sys.argv[i + 1])
            except ValueError:
                pass
    
    run_dispatcher(max_tasks=max_tasks, once=once)