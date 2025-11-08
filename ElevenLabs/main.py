from __future__ import annotations

import base64
import io
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional

import speech_recognition as sr
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from pydub.generators import Sine
from pydub.playback import play

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config import get_settings  # noqa: E402  (import after adjusting sys.path)
from .SnowFlakeLLMClient import SnowflakeLLMClient  # noqa: E402

MCP_PROMPT_PATH = PROJECT_ROOT / "mcp_prompt.txt"
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
WAKE_PHRASES = ("hey kora", "hey cora", "hey korra", "hey kory", "hey core", "hey cor")
GOODBYE_PHRASES = ("bye", "goodbye", "bye kora", "bye cora", "bye korra", "thank you kora", "bye cor")


class KoraAssistant:
    """Shared ElevenLabs + Snowflake helper with wake-word utilities."""

    def __init__(
        self,
        *,
        voice_id: str = DEFAULT_VOICE_ID,
        prompt_path: Path = MCP_PROMPT_PATH,
    ) -> None:
        settings = get_settings()
        api_key = settings.elevenlabs_api_key
        if not api_key:
            raise RuntimeError("ELEVENLABS_API_KEY must be configured.")

        self.client = ElevenLabs(api_key=api_key)
        self.voice_id = voice_id
        self.recognizer = sr.Recognizer()
        self.base_prompt = prompt_path.read_text(encoding="utf-8").strip()
        self.conversation_history: List[str] = []

    # ------------------------------------------------------------------
    # Wake / goodbye helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _matches_any(text: Optional[str], phrases: Iterable[str]) -> bool:
        if not text:
            return False
        normalized = text.lower()
        return any(phrase in normalized for phrase in phrases)

    def should_wake(self, transcript: Optional[str]) -> bool:
        return self._matches_any(transcript, WAKE_PHRASES)

    def should_end(self, transcript: Optional[str]) -> bool:
        return self._matches_any(transcript, GOODBYE_PHRASES)

    # ------------------------------------------------------------------
    # Conversation history helpers
    # ------------------------------------------------------------------
    def append_history(self, speaker: str, text: str) -> None:
        entry = f"{speaker.strip().title()}: {text.strip()}"
        self.conversation_history.append(entry)

    def reset_history(self) -> None:
        self.conversation_history.clear()

    def get_history(self, limit: int = 6) -> List[str]:
        return self.conversation_history[-limit:]

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------
    def build_prompt(
        self,
        *,
        vision_summary: str,
        user_text: str,
        instructions: Optional[str] = None,
        conversation_history: Optional[List[str]] = None,
    ) -> str:
        segments = [self.base_prompt]
        if instructions:
            segments.append(f"Additional instructions:\n{instructions.strip()}")
        history = conversation_history if conversation_history is not None else self.get_history()
        if history:
            segments.append("Conversation so far:\n" + "\n".join(history))
        segments.append(f"Vision context:\n{vision_summary.strip()}")
        segments.append(f"User:\n{user_text.strip()}\nAssistant:")
        return "\n\n".join(segments)

    # ------------------------------------------------------------------
    # Speech helpers
    # ------------------------------------------------------------------
    def synthesize(self, text: str) -> bytes:
        response = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            model_id="eleven_turbo_v2",
            voice_settings=VoiceSettings(
                stability=0.0,
                similarity_boost=1.0,
                style=0.0,
                use_speaker_boost=True,
            ),
        )
        audio_bytes = bytearray()
        for chunk in response:
            if chunk:
                audio_bytes.extend(chunk)
        return bytes(audio_bytes)

    def play_text(self, text: str) -> None:
        audio_bytes = self.synthesize(text)
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        play(audio_segment)

    def transcribe_base64(self, audio_base64: str) -> Optional[str]:
        try:
            raw = base64.b64decode(audio_base64)
        except (ValueError, TypeError):
            return None
        return self._transcribe_raw(raw)

    def _transcribe_raw(self, raw_audio: bytes) -> Optional[str]:
        audio_segment = AudioSegment.from_file(io.BytesIO(raw_audio))
        wav_io = io.BytesIO()
        audio_segment.export(wav_io, format="wav")
        wav_io.seek(0)
        with sr.AudioFile(wav_io) as source:
            audio_data = self.recognizer.record(source)
        return self._recognize(audio_data)

    def listen_blocking(
        self,
        *,
        timeout: float = 5.0,
        phrase_time_limit: float = 10.0,
    ) -> Optional[str]:
        with sr.Microphone() as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
            except sr.WaitTimeoutError:
                return None
        return self._recognize(audio)

    def _recognize(self, audio_data: sr.AudioData) -> Optional[str]:
        try:
            transcript = self.recognizer.recognize_google(audio_data)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            print(f"[VOICE] Speech recognition service unavailable: {exc}")
            return None
        return transcript.strip() or None


assistant = KoraAssistant()


def get_assistant() -> KoraAssistant:
    return assistant


# ----------------------------------------------------------------------
# Optional CLI entry point (preserves teammate workflow)
# ----------------------------------------------------------------------
def _play_listening_beep() -> None:
    beep = Sine(440).to_audio_segment(duration=200)
    play(beep)


def _play_processing_beep() -> None:
    beep1 = Sine(440).to_audio_segment(duration=100)
    silence = AudioSegment.silent(duration=100)
    beep2 = Sine(520).to_audio_segment(duration=100)
    play(beep1 + silence + beep2)


def conversation_loop() -> None:
    """Legacy CLI loop for teammates."""
    llm_client = SnowflakeLLMClient()
    conv_active = False
    inactivity_deadline = 0.0
    print("\nSay 'Hey Kora' to start. Say 'bye' to exit.\n")
    try:
        while True:
            transcript = assistant.listen_blocking()
            if not transcript:
                if conv_active and time.time() > inactivity_deadline:
                    print("[WAKE] Conversation timed out.")
                    conv_active = False
                    assistant.reset_history()
                continue

            print(f"[VOICE] Heard: {transcript}")
            if not conv_active:
                if assistant.should_wake(transcript):
                    conv_active = True
                    assistant.reset_history()
                    inactivity_deadline = time.time() + 20
                    assistant.play_text("I'm listening.")
                continue

            inactivity_deadline = time.time() + 20
            if assistant.should_end(transcript):
                assistant.play_text("Goodbye! Stay safe.")
                conv_active = False
                assistant.reset_history()
                continue

            assistant.append_history("User", transcript)
            prompt = assistant.build_prompt(
                vision_summary="No visual context in CLI mode.",
                user_text=transcript,
                conversation_history=assistant.get_history(),
            )
            _play_processing_beep()
            response = llm_client.get_response(prompt) or "I'm sorry, I didn't catch that."
            assistant.append_history("Assistant", response)
            assistant.play_text(response)
    except KeyboardInterrupt:
        print("\n[CLI] Interrupted by user.")
    finally:
        llm_client.close()


if __name__ == "__main__":
    conversation_loop()
