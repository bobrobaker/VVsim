#!/usr/bin/env python3
"""
claude-backlog.py — view and sort your Claude Code suggestion backlog
Usage:
  python claude-backlog.py [task-list-name]   # specific session UUID
  python claude-backlog.py --latest           # most recently modified session
  python claude-backlog.py --all              # all sessions combined
Or set CLAUDE_CODE_TASK_LIST_ID in your environment.
"""

import json
import os
import sys
from pathlib import Path

TASK_DIR = Path.home() / ".claude" / "tasks"


def latest_list():
    dirs = [d for d in TASK_DIR.iterdir() if d.is_dir()]
    if not dirs:
        print("No task lists found in ~/.claude/tasks/")
        sys.exit(1)
    return max(dirs, key=lambda d: d.stat().st_mtime).name


def load_tasks_from(list_name):
    task_path = TASK_DIR / list_name
    if not task_path.exists():
        print(f"No task list found at {task_path}")
        sys.exit(1)
    tasks = []
    for f in task_path.glob("*.json"):
        try:
            tasks.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            print(f"Warning: could not parse {f.name}")
    return tasks


arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_CODE_TASK_LIST_ID", "")

if arg == "--latest":
    list_names = [latest_list()]
elif arg == "--all":
    list_names = [d.name for d in TASK_DIR.iterdir() if d.is_dir()] if TASK_DIR.exists() else []
elif arg:
    list_names = [arg]
else:
    print("Usage: python claude-backlog.py <session-uuid|--latest|--all>")
    print("Or set CLAUDE_CODE_TASK_LIST_ID in your environment")
    sys.exit(1)

VALUE_ORDER = {"high": 0, "medium": 1, "low": 2, "": 3}


def extract_field(description, field):
    for line in (description or "").splitlines():
        if line.strip().startswith(f"{field}:"):
            return line.split(":", 1)[-1].strip()
    return ""


def sort_key(t):
    desc = t.get("description", "")
    value = extract_field(desc, "VALUE").lower()
    effort = extract_field(desc, "EFFORT").lower()
    return (VALUE_ORDER.get(value, 3), VALUE_ORDER.get(effort, 3))


all_suggestions = []
for list_name in list_names:
    tasks = load_tasks_from(list_name)
    suggestions = [
        t for t in tasks
        if t.get("subject", "").startswith("[SUGGESTION]")
        and t.get("status") != "completed"
    ]
    all_suggestions.extend(suggestions)

all_suggestions.sort(key=sort_key)

label = arg if arg not in ("--latest", "--all") else arg
print(f"\n{'='*60}")
print(f"BACKLOG: {label}  ({len(all_suggestions)} open suggestions)")
print(f"{'='*60}\n")

for t in all_suggestions:
    desc = t.get("description", "")
    print(f"  ID:      {t.get('id', '?')}")
    print(f"  Subject: {t.get('subject', '?')}")
    print(f"  Status:  {t.get('status', '?')}")
    print(f"  Value:   {extract_field(desc, 'VALUE')}  |  Effort: {extract_field(desc, 'EFFORT')}")
    print(f"  File:    {extract_field(desc, 'FILE')}")
    print(f"  Trigger: {extract_field(desc, 'TRIGGER')}")
    print(f"  Goal:    {extract_field(desc, 'GOAL')}")
    print(f"  Grep:    {extract_field(desc, 'GREP')}")
    if t.get("blockedBy"):
        print(f"  Blocked: {t.get('blockedBy')}")
    print()
