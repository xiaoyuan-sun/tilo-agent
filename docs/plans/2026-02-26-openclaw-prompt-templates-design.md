# OpenClaw-Style Prompt Templates Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce a project-centered prompt system that only uses `AGENTS.md`, `SOUL.md`, `USER.md`, `MEMORY.md`, and `BOOTSTRAP.md`, with auto-initialization in each user workspace when files are missing.

**Architecture:** Add a prompt-template module that owns default file contents and workspace initialization, then compose system prompt text from these files at runtime. Keep tool protocol and runtime behavior unchanged except prompt source and per-user memory routing.

**Tech Stack:** Python 3.12, unittest, existing AgentScope runtime integration.

---

### Task 1: Add failing tests for prompt file initialization

**Files:**
- Create: `tests/test_prompt_files.py`
- Modify: none

1. Write test asserting first call creates all five markdown files in a user workspace.
2. Run test and verify it fails due to missing module/function.
3. Commit only after implementation passes.

### Task 2: Add failing tests for prompt composition from files

**Files:**
- Modify: `tests/test_prompt_files.py`

1. Write test asserting system prompt includes file contents (AGENTS/SOUL/USER/MEMORY/BOOTSTRAP).
2. Run test and verify expected failure.

### Task 3: Implement prompt template and initializer module

**Files:**
- Create: `src/agent/prompt_files.py`
- Create: `src/prompts/AGENTS.md`
- Create: `src/prompts/SOUL.md`
- Create: `src/prompts/USER.md`
- Create: `src/prompts/MEMORY.md`
- Create: `src/prompts/BOOTSTRAP.md`

1. Add default templates.
2. Add function to initialize missing files in workspace.
3. Add function to read and compose final prompt context text.

### Task 4: Wire runtime to use prompt files and user-isolated memory

**Files:**
- Modify: `src/agent/prompt_builder.py`
- Modify: `src/agent/core.py`

1. Update system prompt builder signature and prompt text to embed prompt-file context.
2. Ensure `run_once` initializes prompt files and builds prompt from workspace files.
3. Route memory load/append by `ctx.user_id` for isolation.

### Task 5: Verification

**Files:**
- Modify: any tests touched above

1. Run targeted tests for new prompt features.
2. Run full test suite.
3. Report results with command evidence.
