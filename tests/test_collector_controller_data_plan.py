"""Pure review-plan checks; no live paths are opened or changed."""
import unittest

from youtube_ops.collector_controller_data_plan import controller_data_plan, SOURCE, TARGET


class ControllerDataPlanTests(unittest.TestCase):
    def test_fixed_private_target_preserves_narrator_and_existing_ledger(self):
        plan = controller_data_plan(native_report_sha256='a' * 64)
        self.assertEqual(plan['source_ledger'], SOURCE + '/narrator-control.sqlite')
        self.assertEqual(plan['target_ledger'], TARGET + '/narrator-control.sqlite')
        self.assertEqual(plan['narration_job_spool_retained'], SOURCE)
        self.assertTrue(plan['source_retained'])
        self.assertFalse(plan['executable'])
        self.assertEqual(len(plan['unresolved_pins']), 3)

    def test_complete_hashes_still_do_not_authorize_a_cutover(self):
        plan = controller_data_plan(native_report_sha256='a' * 64, ledger_sha256='b' * 64,
                                    code_manifest_sha256='c' * 64, old_task_xml_sha256='d' * 64)
        self.assertEqual(plan['status'], 'REVIEW_PLAN_ONLY')
        self.assertTrue(plan['owner_approval_required'])
        self.assertTrue(plan['live_native_acceptance_required'])
        self.assertEqual(plan['unresolved_pins'], [])
        self.assertIn('uncertain outcome holds', plan['steps'][4])
        self.assertIn('zero instances', plan['steps'][5])
        self.assertIn('No activity', plan['rollback_requires'][2])

    def test_unreviewed_or_missing_digest_is_refused(self):
        for value in (None, True, 'not-a-digest', 'A' * 64):
            with self.subTest(value=value), self.assertRaises(ValueError):
                controller_data_plan(native_report_sha256=value)
