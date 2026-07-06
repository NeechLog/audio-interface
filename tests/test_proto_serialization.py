import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT_DIR / "scripts" / ".env"
DUMMY_AUDIO_FILE = ROOT_DIR / "tests" / "fixtures" / "dummy_audio.wav"


def _load_output_dir() -> Path:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith("OUTPUT_DIR="):
                return Path(line.split("=", 1)[1]).expanduser()

    return ROOT_DIR / "generated_packages"


PACKAGES_DIR = _load_output_dir() / "packages"
for package_name in ("audiomessages", "transcribeclient", "audiocloneclient"):
    sys.path.insert(0, str(PACKAGES_DIR / package_name))

from audiocloneclient import clone_interface_pb2
from audiomessages import AudioMessage, AudioMessageInfo
from transcribeclient import transcribe_interface_pb2


class ProtoSerializationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dummy_audio_bytes = DUMMY_AUDIO_FILE.read_bytes()

    def assert_serialization_round_trip(self, message, message_type):
        serialized = message.SerializeToString(deterministic=True)
        parsed = message_type()
        parsed.ParseFromString(serialized)

        self.assertEqual(parsed.SerializeToString(deterministic=True), serialized)
        return parsed

    def test_audio_message_round_trip(self):
        message = AudioMessage(
            text="hello",
            audio_binary=self.dummy_audio_bytes,
            audio_file_path=str(DUMMY_AUDIO_FILE),
            locale="en-US",
            audio_generator_model_name_version=AudioMessageInfo(
                name="tts",
                value="1.0.0",
                description="dummy generator",
            ),
            text_generator_model_name_version=AudioMessageInfo(
                name="asr",
                value="2.0.0",
                description="dummy transcriber",
            ),
            info=[
                AudioMessageInfo(name="source", value="unit-test"),
                AudioMessageInfo(name="format", value="wav"),
            ],
        )

        parsed = self.assert_serialization_round_trip(message, AudioMessage)

        self.assertEqual(parsed.text, "hello")
        self.assertEqual(parsed.audio_binary, self.dummy_audio_bytes)
        self.assertEqual(parsed.audio_file_path, str(DUMMY_AUDIO_FILE))
        self.assertEqual(parsed.locale, "en-US")
        self.assertEqual(parsed.audio_generator_model_name_version.name, "tts")
        self.assertEqual(parsed.text_generator_model_name_version.value, "2.0.0")
        self.assertEqual([item.name for item in parsed.info], ["source", "format"])

    def test_transcribe_request_round_trip_uses_audio_message_package(self):
        self.assertEqual(
            transcribe_interface_pb2.TranscribeRequest.DESCRIPTOR.fields_by_name[
                "input"
            ].message_type.full_name,
            AudioMessage.DESCRIPTOR.full_name,
        )

        request = transcribe_interface_pb2.TranscribeRequest(
            input=AudioMessage(
                text="hello",
                audio_binary=self.dummy_audio_bytes,
                locale="en-US",
            ),
            model_name="test-asr",
        )

        parsed = self.assert_serialization_round_trip(
            request,
            transcribe_interface_pb2.TranscribeRequest,
        )

        self.assertIsInstance(parsed.input, AudioMessage)
        self.assertEqual(parsed.input.text, "hello")
        self.assertEqual(parsed.input.audio_binary, self.dummy_audio_bytes)
        self.assertEqual(parsed.input.locale, "en-US")
        self.assertEqual(parsed.model_name, "test-asr")

    def test_clone_request_round_trip_uses_audio_message_package(self):
        self.assertEqual(
            clone_interface_pb2.CloneRequest.DESCRIPTOR.fields_by_name[
                "request_audio_message"
            ].message_type.full_name,
            AudioMessage.DESCRIPTOR.full_name,
        )
        self.assertEqual(
            clone_interface_pb2.CloneRequest.DESCRIPTOR.fields_by_name[
                "sample_audio_message"
            ].message_type.full_name,
            AudioMessage.DESCRIPTOR.full_name,
        )

        request = clone_interface_pb2.CloneRequest(
            request_audio_message=AudioMessage(text="speak this", locale="en-US"),
            sample_audio_message=AudioMessage(
                text="sample text",
                audio_binary=self.dummy_audio_bytes,
                locale="en-US",
            ),
            model_name="test-clone",
        )

        parsed = self.assert_serialization_round_trip(
            request,
            clone_interface_pb2.CloneRequest,
        )

        self.assertIsInstance(parsed.request_audio_message, AudioMessage)
        self.assertIsInstance(parsed.sample_audio_message, AudioMessage)
        self.assertEqual(parsed.request_audio_message.text, "speak this")
        self.assertEqual(parsed.sample_audio_message.text, "sample text")
        self.assertEqual(parsed.sample_audio_message.audio_binary, self.dummy_audio_bytes)
        self.assertEqual(parsed.model_name, "test-clone")


if __name__ == "__main__":
    unittest.main()
