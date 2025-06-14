# Privacy Policy

Script to Speech is committed to protecting your privacy and data. This document explains what data is collected, how it's used, and what you should know about third-party services when using this tool.

## Data Collection by Script to Speech

**Script to Speech collects NO user data.** Specifically:

- **No telemetry or analytics**: The application does not send usage statistics, error reports, or any other data about your usage
- **No tracking**: No user behavior is monitored or recorded
- **No advertisements**: No ads are displayed or user data sold to advertisers
- **No data sharing**: Script to Speech does not share any user data with third parties
- **No network requests**: The application only makes network requests to services required for functionality that you explicitly configure
- **No remote logging**: All logs are stored locally on your machine
- **No user accounts**: No registration, login, or user account system exists

## Local Data Storage

Script to Speech stores data locally on your machine:

- **Input files**: Screenplay PDFs/TXT files are copied to `input/[screenplay_name]/` directory
- **Generated files**: Parsed JSON, voice configurations, and audio files are stored in `input/` and `output/` directories
- **Cache files**: Audio clips are cached locally in `output/[screenplay_name]/cache/`
- **Log files**: Processing logs are stored in `output/[screenplay_name]/logs/`

**You have full control** over all local data and can delete any files at any time.

## Data Sent to External Services for Functionality

Script to Speech requires external services to provide its core functionality. Here's what data is sent and why:

### Audio Generation (Required for TTS Functionality)

To convert your screenplay text into speech, Script to Speech sends individual dialogue chunks to TTS (text-to-speech) providers you configure. Support for local, self-hosted, TTS providers is on teh Script to Speech roadmap.

**TTS Providers that may receive your content, if configured:**
- OpenAI
- ElevenLabs
- Cartesia
- Minimax
- Zonos

**Data sent**: Individual dialogue chunks (typically single lines of dialogue or scene descriptions) are sent one at a time to generate audio. Your screenplay is not sent as a complete document to TTS providers.

### Voice Casting (Optional Feature)

If you choose to use the LLM-assisted voice casting feature (`sts-generate-character-notes-prompt`), this is entirely optional and can be skipped.

**LLM Services (when you choose to use voice casting):**

**Data sent**: 
- Your complete screenplay text
- Your current voice configuration
- Instructions for voice casting analysis

**Important**: This optional feature sends your ENTIRE screenplay to the LLM service. Only use this feature with LLM providers whose privacy policies you trust, or skip this feature entirely and configure voices manually.

## What You Should Know About Third-Party Services

Each service has different policies regarding:

- **Data retention**: How long they keep your content
- **Data usage**: Whether your content is used for training AI models
- **Data sharing**: Whether your content is shared with other parties
- **Geographic storage**: Where your data is processed and stored

### Recommended Actions

Before using any service:

1. **Read their privacy policy**: Understand how your data will be handled
2. **Check training data policies**: Determine if your content will be used to train AI models
3. **Review data retention**: Understand how long your content is stored
4. **Consider data sensitivity**: Evaluate whether you're comfortable sharing your screenplay content

### Service-Specific Resources

- **OpenAI**: [Privacy Policy](https://openai.com/privacy/) | [Consumer Privacy / Data use](https://openai.com/consumer-privacy/)
- **ElevenLabs**: [Privacy Policy](https://elevenlabs.io/privacy)
- **Cartesia**: [Privacy Policy](https://cartesia.ai/legal/privacy.html)
- **Minimax**: [Privacy Policy](https://www.minimax.io/audio/doc/privacy-policy.html)
- **Zonos**: [Privacy Policy](https://playground.zyphra.com/settings/data-management)

## Recommendations for Privacy-Conscious Usage

### Minimize Data Exposure

1. **Test with sample content**: Use non-sensitive text for initial testing and voice sampling
2. **Use dummy providers**: Test configurations with `--dummy-tts-provider-override` flag

### Read Privacy / Data Usage Policies
1. Different TTS and LLM providers have different stances on data privacy and usage. Understand which providers use user supplied content for LLM training
2. "Free" tiers for providers often give up privacy and data usage rights in exchange for free usage

### LLM Voice Casting Considerations (Optional Features)

1. **Manual approach**: Skip LLM assistance entirely and configure voices manually - these features are completely optional
2. **Use local LLMs**: Consider running local language models instead of cloud services
3. **Custom prompts**: Create your own voice casting prompts without including screenplay text
4. **Avoid sensitive content**: Don't use voice casting features for confidential screenplays

### API Key Security

1. **Use .env files**: Store API keys locally rather than in environment variables
2. **Rotate keys regularly**: Generate new API keys periodically
3. **Limit key permissions**: Use API keys with minimal required permissions where possible
4. **Monitor usage**: Check provider dashboards for unexpected API usage

### Data Management

1. **Clean up regularly**: Delete cached audio and logs you no longer need
2. **Backup configurations**: Keep voice configurations but consider removing screenplay content from backups
3. **Secure storage**: Store sensitive screenplay files in encrypted directories
4. **Version control**: Avoid committing screenplay content or API keys to version control

## International Users

Different countries have different privacy laws (GDPR, CCPA, etc.). Consider:

- **Data residency**: Where your data is processed by third-party services
- **Legal compliance**: Whether service providers comply with your local privacy laws
- **Data transfer**: How data moves between countries when using cloud services

## Changes to This Policy

This privacy policy may be updated to reflect changes in:

- How Script to Speech operates
- New third-party service integrations
- Legal requirements
- User feedback

Check this file periodically for updates. The last update date is shown at the bottom of this document.

## Contact Information

For privacy-related questions or concerns about Script to Speech:

- **GitHub Issues**: [Create an issue](https://github.com/trentw/script-to-speech/issues) for privacy questions
- **Email**: Contact the maintainer at the email address listed in the project's `pyproject.toml`

For questions about third-party service privacy policies, contact those services directly using the links provided above.

## Your Responsibility

As a user of Script to Speech, you are responsible for:

- Understanding the privacy policies of services you choose to use
- Making informed decisions about what content to process
- Complying with any applicable laws regarding data processing
- Protecting your API keys and sensitive content

## Summary

- **Script to Speech**: Collects no data, operates locally, fully under your control
- **TTS Providers**: Receive individual text lines for audio generation
- **LLM Services**: May receive complete screenplay content when using voice casting features
- **Your choice**: You decide which services to use and what content to process

---

*Last updated: May 30, 2025*