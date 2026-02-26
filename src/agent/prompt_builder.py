SYSTEM_PROMPT = (
    "You are the Tilo agent powered by AgentScope.\n\n"
    "Prompt context files are the single source of truth:\n"
    "{prompt_context}\n\n"
    "Runtime tool protocol:\n"
    "1) Only use tools listed below and emit tool calls as JSON objects matching the TOOL protocol: "
    '{{"name": ..., "args": {{...}}}}.\n'
    "2) Never hallucinate tool names or pretend a tool returned a result you do not have.\n"
    "3) Keep chain-of-thought internal; the assistant response should be concise and not expose reasoning steps.\n"
    "4) When producing the final answer, do so only after you have collected any required tool output.\n"
    "\n"
    "SKILLS SUMMARY:\n{skills_summary}\n"
    "\n"
    "AVAILABLE TOOLS:\n{tool_list}\n"
)


def build_sys_prompt(
    prompt_context: str | None = None,
    tool_list_text: str = "",
    *,
    skills_summary: str | None = None,
) -> str:
    # Backward-compatible alias: existing callers may pass skills_summary.
    resolved_context = prompt_context if prompt_context is not None else skills_summary
    return SYSTEM_PROMPT.format(
        prompt_context=(resolved_context or "").strip() or "(no prompt files available)",
        skills_summary=(resolved_context or "").strip() or "(no skills enabled)",
        tool_list=tool_list_text.strip() or "(no tools registered)",
    )
