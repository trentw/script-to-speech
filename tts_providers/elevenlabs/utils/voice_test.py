from elevenlabs import ElevenLabs, VoiceSettings
import os


def generate_test_audio(voice_id):
    # Initialize ElevenLabs API
    api_key = os.environ.get("ELEVEN_API_KEY")
    if not api_key:
        raise ValueError("ELEVEN_API_KEY environment variable is not set")

    client = ElevenLabs(api_key=api_key)

    # Generate audio with the specified voice_id
    response = client.text_to_speech.convert(
        voice_id=voice_id,
        optimize_streaming_latency="0",
        output_format="mp3_44100_128",
        text="this is a test",
        model_id="eleven_multilingual_v2",
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True,
        ),
    )

    # Save the output as an MP3 file with the voice ID as the filename
    audio_data = b""
    for chunk in response:
        if chunk:
            audio_data += chunk

    file_name = f"{voice_id}.mp3"
    with open(file_name, "wb") as f:
        f.write(audio_data)

    print(f"Audio saved as {file_name}")


if __name__ == "__main__":
    # Example usage: Pass the desired voice_id
    test_voice_id = input("Enter the voice ID to test: ")
    generate_test_audio(test_voice_id)
