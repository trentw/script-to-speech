"""Prompt construction for LLM voice analysis via multimodal LLMs."""

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from script_to_speech.utils.logging import get_screenplay_logger
from script_to_speech.voice_library.constants import REPO_VOICE_LIBRARY_PATH

logger = get_screenplay_logger("llm_voice_labeler.prompt_builder")

# Calibration examples included in every LLM prompt as reference anchors.
# These are well-characterized, hand-labeled voices chosen to span the full
# range of properties (quality, energy, performative, etc.). Provider-specific
# only in the sense that we need known-good ground truth — the labeling
# pipeline itself is provider-agnostic.
CALIBRATION_VOICE_IDS = {
    "openai": ["onyx", "sage", "fable", "alloy", "coral", "shimmer"],
    "elevenlabs": ["callum", "charlie"],
}


def load_schema() -> str:
    """Load the voice library schema YAML as a string."""
    schema_path = REPO_VOICE_LIBRARY_PATH / "voice_library_schema.yaml"
    with open(schema_path, "r") as f:
        return f.read()


def load_calibration_examples(
    providers: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Load hand-labeled calibration examples from known provider voices.yaml files.

    Returns a list of dicts with sts_id, voice_properties, description, tags.
    """
    if providers is None:
        providers = list(CALIBRATION_VOICE_IDS.keys())

    examples = []
    for provider in providers:
        voice_ids = CALIBRATION_VOICE_IDS.get(provider, [])
        if not voice_ids:
            continue

        voices_path = REPO_VOICE_LIBRARY_PATH / provider / "voices.yaml"
        if not voices_path.exists():
            # Try premade variant
            voices_path = REPO_VOICE_LIBRARY_PATH / provider / "voices_premade.yaml"
        if not voices_path.exists():
            logger.warning(f"No voices.yaml found for calibration provider: {provider}")
            continue

        with open(voices_path, "r") as f:
            data = yaml.safe_load(f)

        voices = data.get("voices", {})
        for vid in voice_ids:
            if vid in voices:
                entry = voices[vid]
                examples.append(
                    {
                        "provider": provider,
                        "sts_id": vid,
                        "voice_properties": entry.get("voice_properties", {}),
                        "description": entry.get("description", {}),
                        "tags": entry.get("tags", {}),
                    }
                )

    return examples


def format_calibration_examples(examples: List[Dict[str, Any]]) -> str:
    """Format calibration examples as text for the prompt."""
    if not examples:
        return "No calibration examples available."

    lines = []
    for ex in examples:
        lines.append(f"### {ex['provider']}/{ex['sts_id']}")

        vp = ex.get("voice_properties", {})
        lines.append("voice_properties:")
        for k, v in sorted(vp.items()):
            lines.append(f"  {k}: {v}")

        desc = ex.get("description", {})
        lines.append("description:")
        for k, v in sorted(desc.items()):
            lines.append(f"  {k}: {v}")

        tags = ex.get("tags", {})
        lines.append("tags:")
        for k, v in sorted(tags.items()):
            lines.append(f"  {k}: {v}")

        lines.append("")

    return "\n".join(lines)


def build_system_prompt(
    calibration_providers: Optional[List[str]] = None,
    dual_clips: bool = False,
) -> str:
    """Build the system prompt with schema and calibration examples.

    Args:
        calibration_providers: Which providers to include calibration examples from
        dual_clips: If True, include instructions for analyzing two audio clips
    """
    schema_text = load_schema()
    examples = load_calibration_examples(calibration_providers)
    examples_text = format_calibration_examples(examples)

    if dual_clips:
        audio_instructions = """## Audio Clips

You will receive TWO audio clips of the same voice reading different texts:

1. **NEUTRAL CLIP**: The voice reading calm, conversational content. Use this primarily for grounding NUMERIC properties (pitch, pace, energy baseline).

2. **EXPRESSIVE CLIP**: The voice reading dramatic, varied content (dialogue, action, whispers, shouts). Use this for understanding the voice's CHARACTER — its warmth, roughness, emotional tone, and personality.

**Critical principle**: You are evaluating the VOICE, not the text content. Focus on timbre, tone, texture, warmth, roughness, breathiness, resonance — the qualities that make this voice distinctive regardless of what it's reading.

**How to use both clips together:**
- **energy**: Average across both clips. A voice that's calm on neutral content but animated on dramatic content has moderate energy.
- **performative**: How theatrical is the voice's delivery STYLE? A voice that sounds dramatic even reading a weather report is high-performative. A voice that stays flat reading dramatic dialogue is low-performative. Judge from BOTH clips.
- **range**: How much does the voice change between clips? Big difference = high range.
- **quality**: Assess from BOTH clips — audio artifacts will be present in both.
- **authority, age, pitch, pace**: Intrinsic properties — average your impressions from both clips.
- **description and tags**: Base these primarily on the EXPRESSIVE clip, which reveals the voice's full personality and acting ability. The expressive clip shows what this voice can do when given real content to work with."""
    else:
        audio_instructions = """## Audio Clip

You will receive one audio clip of the voice. Rate the voice's intrinsic properties — focus on the voice itself, not the content being read."""

    authority_guidance = """## Authority Assessment Guide

Listen for vocal weight and consonant sharpness — not just loudness.

Acoustic cues:
- **Resonance**: High-authority voices have strong lower-harmonic resonance (full chest voice). Low-authority voices sound thinner or breathier.
- **Consonant precision**: High-authority voices have sharp, precise plosives (t, k, p sounds are crisp and defined). Low-authority voices have softer consonant attacks.
- **Phrase endings**: High-authority voices sustain energy through the end of phrases. Low-authority voices trail off, fade, or drop into vocal fry at sentence ends.
- **Breathiness**: More breathiness = less authority. A clean, clear phonation = more authority.

Scale:
- **0.0-0.2** = Gentle, soft, breathy — voice trails off, consonants are soft
- **0.3-0.4** = Mild, approachable — some breathiness, moderate consonant definition
- **0.5** = Neutral — balanced, neither commanding nor submissive
- **0.6-0.7** = Confident, firm — clear resonance, precise consonants, sustained phrase energy
- **0.8-1.0** = Commanding, authoritative — powerful chest resonance, sharp articulation, dominant presence"""

    age_guidance = """## Age Assessment Guide

Focus on formant brightness, speech rate, and vocal stability.

Acoustic cues:
- **Formant brightness**: Younger voices have brighter, higher formant frequencies. Older voices have darker, more muffled formants.
- **Speech rate**: Younger voices tend toward brisker articulation. Older voices are typically slower with longer pauses between phrases.
- **Vocal stability**: Younger voices have clean, stable harmonics. Older voices may exhibit micro-instabilities — slight tremor, vocal fry, or gravelly texture in sustained vowels.
- **Pitch**: Elderly male voices may rise slightly in pitch; elderly female voices may drop.

Scale:
- **0.1-0.2** = Child — very bright formants, fast/uncontrolled pacing
- **0.3-0.4** = Young adult — bright, fast, clean and stable
- **0.5** = Adult — moderate formant brightness, natural pacing
- **0.6-0.7** = Middle-aged — slightly darker formants, measured pacing, possibly some texture
- **0.8-0.9** = Elderly — slow pacing, longer pauses, vocal instabilities, gravelly or tremulous quality"""

    pitch_guidance = """## Pitch Assessment Guide

Rate the baseline fundamental frequency (F0) of the speaker, ignoring volume or emotion.

- **0.0-0.2** = Very deep bass — the voice "hums" low in the chest (roughly 80-110 Hz)
- **0.3-0.4** = Low — deep but not rumbling (roughly 110-140 Hz)
- **0.5** = Medium — average speaking pitch
- **0.6-0.7** = High — noticeably higher, sits in the upper register
- **0.8-1.0** = Very high — bright, sits high in the throat/head voice"""

    range_guidance = """## Range Assessment Guide

Measure the variance in pitch and volume across the clip — how much does the voice modulate?

Acoustic cues:
- **Pitch variance (F0 standard deviation)**: Does the pitch tracking move up and down like a melody, or stay flat on one note?
- **Amplitude variance**: Does the voice get noticeably louder on emphasized words and softer on others, or maintain consistent volume?

Scale:
- **0.0-0.2** = Monotone — flat pitch, flat volume, robotic prosody
- **0.3-0.4** = Limited — slight pitch and volume variation, but constrained
- **0.5** = Conversational — natural moderate variation in pitch and volume
- **0.7-0.8** = Expressive — wide melodic pitch swings, noticeable volume dynamics
- **0.9-1.0** = Highly expressive — extreme pitch range, dramatic volume changes"""

    quality_guidance = """## Quality Assessment Guide

The **quality** property measures AUDIO and SPEECH quality — technical fidelity, not voice pleasantness.

**IMPORTANT**: Most modern TTS voices are high quality (0.85-1.0). Only reduce quality below 0.8 if you hear CLEAR, OBVIOUS issues — not subtle ones you have to strain to notice.

- **1.0** = Clean, clear, natural-sounding. No audible artifacts. This is the DEFAULT for a good TTS voice — do not hesitate to rate voices 1.0 if they sound clean.
- **0.85-0.95** = Very good but with minor, occasional issues (a slightly odd inflection, a barely noticeable artifact)
- **0.7-0.8** = Noticeable issues that a listener would pick up: robotic cadence, occasional clipping, audio artifacts
- **0.5-0.6** = Obviously problematic: blown-out plosives, choppy transitions, clearly robotic, unnatural pauses
- **Below 0.5** = Significant issues: heavy distortion, very robotic, hard to listen to

Do NOT confuse voice CHARACTER with quality. A deep gravelly voice can be quality=1.0 if the audio is clean. An unusual-sounding voice is not lower quality just because it sounds different."""

    energy_guidance = """## Energy Assessment Guide

**IMPORTANT**: Decouple the SOUND from the MEANING of the words. Ignore what the text says — listen only to the acoustic properties of the voice itself.

Listen for these specific acoustic cues:
- **Pitch variance**: Does the voice stay in a narrow, flat frequency range, or does it bounce high and low across sentences? Wide pitch movement = higher energy.
- **Amplitude spikes**: Are stressed syllables noticeably louder than unstressed syllables, or is the volume flat and consistent? Sharp volume spikes on stressed words = higher energy.
- **Consonant attack**: Are consonants soft and blended, or sharp, crisp, and percussive? Hard consonant attacks = higher energy.
- **Tempo**: Is the speaking rate measured and deliberate, or brisk and urgent?

Scale:
- **0.0-0.2** = Acoustically flat: narrow pitch range, slow/measured pacing, soft consonant attacks, highly compressed volume
- **0.3-0.4** = Restrained: slight pitch movement, smooth delivery, minimal volume spikes (e.g., late-night radio host, bedtime story)
- **0.5** = Conversational: natural, moderate pitch variation and pacing, typical of everyday casual speech
- **0.7-0.8** = Acoustically bright: wide pitch range, brisk pacing, sharp consonant attacks, noticeable volume spikes on stressed words (e.g., morning news anchor, enthusiastic teacher)
- **0.9-1.0** = Highly dynamic: extreme pitch bouncing, rapid pacing, very sharp articulation, aggressive volume changes"""

    performative_guidance = """## Performative Assessment Guide

**IMPORTANT**: Performative measures theatrical EXAGGERATION and voice acting — not loudness or energy (those are separate properties). A voice can be high-energy but not performative (fast-talking auctioneer), or performative but low-energy (creepy whispering villain).

Listen for these specific acoustic cues:
- **Micro-pauses for effect**: Does the voice insert dramatic pauses before key words or reveals?
- **Timbre shifts**: Does the voice change its actual TEXTURE — shifting from full-chested speech to breathy whispers, or from calm narration to urgent shouting? Same texture throughout = low performative.
- **Vowel elongation**: Does the voice stretch vowels on emotional words for dramatic weight?
- **Non-verbal vocalizations**: Audible breaths, sighs, gasps, or pushed/breathy laughs indicate voice acting.

Scale:
- **0.0-0.2** = Informational/robotic: straightforward reading, uniform vocal texture, standard pauses, sounds like reading a textbook
- **0.3-0.4** = Subdued: slight emotional inflection, but maintains a consistent, restrained persona
- **0.5** = Natural/conversational: moderate inflection matching the text, but not exaggerated
- **0.6-0.7** = Animated: noticeable emotional coloring, some dramatic pauses, shifts in vocal texture between different content
- **0.8-1.0** = Theatrical: heavy voice acting — dramatic micro-pauses, extreme timbre shifts (whisper to shout), elongated vowels, audible breaths/sighs for effect"""

    return f"""You are an expert voice analyst. Your task is to listen to audio sample(s) of a text-to-speech voice and classify its properties according to a standardized schema.

{audio_instructions}

## Voice Library Schema

The following schema defines all properties you must evaluate. Pay careful attention to the scale points for range properties and the allowed values for enum properties.

```yaml
{schema_text}
```

{authority_guidance}

{age_guidance}

{pitch_guidance}

{range_guidance}

{quality_guidance}

{energy_guidance}

{performative_guidance}

## Calibration Examples

These are hand-labeled examples from known voices. Use them to calibrate your ratings. Note the relationship between the numeric values and the voice characteristics described.

{examples_text}

## Instructions

1. Listen carefully to the entire audio sample(s)
2. For each **range property** (age, authority, energy, pace, performative, pitch, quality, range): assign a value between 0.0 and 1.0 using the scale points and assessment guides above. Use increments of 0.05 for precision.
3. For **enum properties** (accent, gender): select exactly one value from the allowed list
4. For **text properties** (special_vocal_characteristics): provide a brief description if applicable, or null if none
5. Write a **custom_description**: 1-2 sentences capturing what makes this voice distinctive. Focus on the voice's TIMBRE and CHARACTER (warm, gravelly, bright, breathy, resonant, etc.), not on what text it's reading or how well it performs. Think: "If I closed my eyes, what kind of person would I imagine speaking?"
6. Estimate **perceived_age**: an age range like "25-40 years"
7. Suggest **character_types**: 3-6 character archetypes from screenplays/audiobooks this voice would be cast as. Think about the voice's tone, authority level, and personality — NOT about what it's reading in the sample. Prefer tags from this vocabulary (but you may add new ones): protagonist, friend, narrator, teacher, professional, news, doctor, father, student, coach, villain, butler, grandfather, boss, businessman, therapist, son, child, teen, professor, detective, hero, sidekick, authority_figure, mother, storyteller, cowboy, husband, orator, adventurer, police, judge, caregiver, assistant, lawyer, antagonist, witch, angry_customer, guide, news_anchor, cheerleader, marketer, older_man, wiseman, sheriff, advisor, sage, bartender, king, bard, shopkeeper, background, extra, businesswoman, girlfriend, farmer, scientist, pirate, superhero, presenter, receptionist, nurse, influencer, knight, priest
8. Suggest **custom_tags**: 3-8 descriptive tags about the voice's SONIC qualities and personality. Prefer tags from this vocabulary (but you may add new ones): neutral, natural, friendly, conversational, warm, calm, even, expressive, confident, enthusiastic, deep, engaging, young, approachable, trustworthy, smooth, helpful, subdued, energetic, soothing, gentle, optimistic, thoughtful, professional, measured, genuine, precise, edgy, gruff, stern, angry, emotional, proper, classy, spirited, encouraging, caring, kind, jolly, charming, direct, assertive, poetic, upbeat, exaggerated, regal, raspy, curious, soft, laid_back, cheerful, gravelly, commanding, reflective, patient, wise, sassy, sinister, foreboding, supportive, breathy, sultry, passionate, relaxed, bubbly, playful, formal, reserved, droning, bored

Return your analysis as a JSON object with this exact structure:
```json
{{
  "voice_properties": {{
    "accent": "<enum value>",
    "gender": "<enum value>",
    "age": <float>,
    "authority": <float>,
    "energy": <float>,
    "pace": <float>,
    "performative": <float>,
    "pitch": <float>,
    "quality": <float>,
    "range": <float>,
    "special_vocal_characteristics": "<string or null>"
  }},
  "reasoning": {{
    "energy": "<1-2 sentences: what specific acoustic cues did you hear? pitch movement, amplitude spikes, consonant attacks, tempo?>",
    "performative": "<1-2 sentences: what specific cues? micro-pauses, timbre shifts, vowel elongation, non-verbal sounds?>",
    "quality": "<1-2 sentences: any artifacts, robotic cadence, clipping, or is the audio clean?>",
    "range": "<1-2 sentences: how much pitch/volume variance across the clips?>",
    "authority": "<1-2 sentences: resonance, consonant precision, phrase-ending energy?>"
  }},
  "description": {{
    "custom_description": "<string>",
    "perceived_age": "<string>"
  }},
  "tags": {{
    "character_types": ["<string>", ...],
    "custom_tags": ["<string>", ...]
  }}
}}
```

Be precise and consistent. Use the calibration examples and assessment guides to anchor your ratings."""


def build_user_message(
    provider_info: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the user message for a single voice analysis.

    Args:
        provider_info: Optional provider metadata (provider_name, provider_description, etc.)
    """
    parts = [
        "Please analyze the attached audio sample and provide voice property ratings."
    ]

    if provider_info:
        parts.append("\n## Provider Context")
        if "provider_name" in provider_info:
            parts.append(f"Voice name: {provider_info['provider_name']}")
        if "provider_description" in provider_info:
            parts.append(
                f"Provider description: {provider_info['provider_description']}"
            )
        if "provider_use_cases" in provider_info:
            parts.append(f"Suggested use cases: {provider_info['provider_use_cases']}")
        parts.append(
            "\nUse these hints to inform your description, tags, and character_types, "
            "but base all numeric ratings on what you actually hear in the audio."
        )

    parts.append("\nReturn ONLY the JSON object, no other text.")
    return "\n".join(parts)
