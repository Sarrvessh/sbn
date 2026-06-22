"""Mock governance checks for intercepted prompts."""


def is_prompt_flagged(prompt: str) -> bool:
    """Flag trace if prompt contains sensitive keyword `secret`."""

    return "secret" in prompt.lower()
