"""Preserve managed music across native numeric serialization, without tolerances."""
import copy
import unittest
from unittest.mock import Mock

from youtube_ops.collector_editor_fixture import checked_music, music_fingerprint


class MusicIdentityTests(unittest.TestCase):
    def setUp(self):
        self.original = {'id': 'music', 'position': 0, 'start': 0, 'end': 40.6,
                         'volume': {'Points': [{'co': {'X': 1, 'Y': .15000000596046448},
                                               'interpolation': 0}]}}
        self.previous = {'managed_music': [{'clip_id': 'music',
                                           'sha256': music_fingerprint(self.original)}]}

    def check(self, current, previous=None):
        client = Mock()
        client._invoke.return_value = {'data': current}
        result = checked_music(client, [{'id': 'music', 'layer': 2}], 2,
                               self.previous if previous is None else previous)
        client._invoke.assert_called_once_with(['clip', 'get', 'music'])
        return result

    def test_native_integer_to_float_reopen_preserves_original_ownership_receipt(self):
        current = dict(self.original, position=0.0, start=0.0)
        self.assertNotEqual(music_fingerprint(current), self.previous['managed_music'][0]['sha256'])
        before = copy.deepcopy(self.previous)
        self.assertEqual(self.check(current), [current])
        self.assertEqual(self.previous, before)

    def test_existing_float_and_mixed_time_receipts_remain_supported(self):
        for position, start in ((0.0, 0.0), (0, 0.0), (0.0, 0)):
            original = dict(self.original, position=position, start=start)
            previous = {'managed_music': [{'clip_id': 'music', 'sha256': music_fingerprint(original)}]}
            self.assertEqual(self.check(self.original, previous), [self.original])
        original = dict(self.original, position=-0.0)
        previous = {'managed_music': [{'clip_id': 'music', 'sha256': music_fingerprint(original)}]}
        self.assertEqual(self.check(original, previous), [original])

    def test_real_timing_and_gain_changes_still_block_even_below_float32_precision(self):
        for key, value in (('position', .000000001), ('start', .000000001), ('end', 40.600000001)):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'Music gain or timing was changed'):
                self.check(dict(self.original, **{key: value}))
        current = copy.deepcopy(self.original)
        current['volume']['Points'][0]['co']['Y'] += .000000001
        with self.assertRaisesRegex(ValueError, 'Music gain or timing was changed'):
            self.check(current)

    def test_curve_shape_and_boolean_time_changes_remain_blocked(self):
        current = copy.deepcopy(self.original)
        current['volume']['Points'][0]['interpolation'] = 1
        for changed in (current, dict(self.original, position=False)):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, 'Music gain or timing was changed'):
                self.check(changed)


if __name__ == '__main__':
    unittest.main()
