"""Shared fixtures for LLM voice labeler tests."""


def make_run(
    age=0.5,
    authority=0.5,
    energy=0.5,
    pace=0.5,
    performative=0.5,
    pitch=0.5,
    quality=0.9,
    range_val=0.5,
    accent="american",
    gender="male",
    special_vocal_characteristics=None,
    custom_description="A clear, natural voice.",
    perceived_age="30-40 years",
    character_types=None,
    custom_tags=None,
    reasoning=None,
    **overrides,
):
    """Build a minimal valid run result dict for consensus testing."""
    result = {
        "voice_properties": {
            "age": age,
            "authority": authority,
            "energy": energy,
            "pace": pace,
            "performative": performative,
            "pitch": pitch,
            "quality": quality,
            "range": range_val,
            "accent": accent,
            "gender": gender,
        },
        "description": {
            "custom_description": custom_description,
            "perceived_age": perceived_age,
        },
        "tags": {
            "character_types": character_types or ["narrator"],
            "custom_tags": custom_tags or ["calm", "natural"],
        },
    }
    if special_vocal_characteristics is not None:
        result["voice_properties"][
            "special_vocal_characteristics"
        ] = special_vocal_characteristics
    if reasoning is not None:
        result["reasoning"] = reasoning
    result.update(overrides)
    return result
