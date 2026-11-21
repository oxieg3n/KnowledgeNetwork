"""V9 must never revive the old API through saved V8 environment settings."""
import contextlib
import io
import unittest
from unittest.mock import patch

from youtube_ops.collector_voice import RemoteVoiceStudioProvider, VoiceError, main


class RetiredVoiceTests(unittest.TestCase):
    def test_old_entrypoints_fail_before_network_or_credentials(self):
        with patch.object(RemoteVoiceStudioProvider, '__init__') as create:
            with self.assertRaisesRegex(VoiceError, 'VOICESTUDIO_PROVIDER_RETIRED'):
                RemoteVoiceStudioProvider.from_environment()
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(['generate']), 1)
            self.assertIn('VOICESTUDIO_PROVIDER_RETIRED', output.getvalue())
            create.assert_not_called()
