from .schemas import GuidanceRequest

SYSTEM_PROMPT = (
    "You are IRA’s guidance module inside a VS Code extension for novice Python learners. "
    "Generate three-tier help for a specific Python error in a specific code context.\n\n"
    "Rules:\n"
    "- Write simply, concretely, and concisely.\n"
    "- Tier 1 is a single sentence definition of the exact error type.\n"
    "- Tier 2 explains why it happened in this user's code and how to fix it, in 2 to 4 short sentences; include a reusable debugging move.\n"
    "- Tier 3 provides the actual fix in context. Prefer a small unified diff plus a corrected snippet. "
    "If uncertain, state what info is missing and give the smallest experiment to confirm.\n"
    "- Return VALID JSON only matching the schema. No markdown fences, no extra commentary.\n"
    "- Never invent APIs or code that would not run. Assume Python 3.11 unless specified."
)

def build_user_prompt(req: GuidanceRequest) -> str:
    parts = [
        "User context:",
        f"- error_type: {req.error_type}",
        f"- pem_text: {req.pem_text}",
        f"- filename: {req.filename or 'unknown'}",
        "- user_code:",
        req.user_code,
        "",
        "Additional context:",
        f"- cursor_line: {req.cursor_line if req.cursor_line is not None else 'unknown'}",
        f"- prior_attempts_summary: {req.prior_attempts or 'none'}",
        f"- project_constraints: {req.constraints or 'none'}",
        "",
        "Task:",
        "Produce Tier 1, Tier 2, and Tier 3 per the schema.",
        "Details:",
        "- Keep Tier 1 to a single sentence.",
        "- Make Tier 2 no more than 4 short sentences.",
        "- For Tier 3, prefer a minimal diff. Only include full patched_code if the snippet is under 120 lines.",
        "- If uncertain, set tier3.confidence below 0.6 and describe the smallest confirmation step.",
        "",
        "Return JSON only."
    ]
    return "\n".join(parts)
