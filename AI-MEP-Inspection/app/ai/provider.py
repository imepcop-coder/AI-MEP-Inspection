from app.config import AI_PROVIDER


def analyze_image(image_path: str):
    """
    Dispatch image analysis to the configured AI provider.
    """

    provider = (AI_PROVIDER or "nvidia").strip().lower()

    if provider == "nvidia":
        from app.ai.nvidia import analyze_image as analyzer
        return analyzer(image_path)

    if provider == "gemini":
        from app.ai.gemini import analyze_image as analyzer
        return analyzer(image_path)

    from app.ai.nvidia import analyze_image as analyzer
    return analyzer(image_path)


def generate_text(prompt: str, system_prompt: str | None = None) -> str:
    provider = (AI_PROVIDER or "nvidia").strip().lower()

    if provider == "nvidia":
        from app.ai.nvidia import generate_text as generator
        return generator(prompt, system_prompt)

    if provider == "gemini":
        from app.ai.gemini import generate_text as generator
        return generator(prompt, system_prompt)

    from app.ai.nvidia import generate_text as generator
    return generator(prompt, system_prompt)
