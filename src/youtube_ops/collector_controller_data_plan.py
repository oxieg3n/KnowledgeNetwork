"""Review-only controller-data cutover plan. No filesystem or service executor."""
import re


SOURCE = 'D:/projects/knowledgenetwork/collector-narrator-v9-004/private-service-v9-001'
TARGET = 'C:/ProgramData/KnowledgeNetworkCollector/NarratorControl'


def controller_data_plan(*, native_report_sha256, ledger_sha256=None,
                         code_manifest_sha256=None, old_task_xml_sha256=None):
    pins = {'native_report_sha256': native_report_sha256, 'ledger_sha256': ledger_sha256,
            'code_manifest_sha256': code_manifest_sha256, 'old_task_xml_sha256': old_task_xml_sha256}
    for name, value in pins.items():
        if value is not None and (not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value)):
            raise ValueError('Invalid reviewed digest: ' + name)
    if native_report_sha256 is None:
        raise ValueError('Native ancestor observation digest required')
    return {
        'schema_version': 1, 'status': 'REVIEW_PLAN_ONLY', 'executable': False,
        'owner_approval_required': True, 'live_native_acceptance_required': True,
        'pins': pins, 'unresolved_pins': [name for name, value in pins.items() if value is None],
        'source_ledger': SOURCE + '/narrator-control.sqlite',
        'target_ledger': TARGET + '/narrator-control.sqlite',
        'target_startup_logs': TARGET + '/review',
        'stage_ledger': TARGET + '/narrator-control.sqlite.stage',
        'migration_journal': TARGET + '/migration-state.private.json',
        'source_retained': True, 'narration_job_spool_retained': SOURCE,
        'code_and_configuration': 'Existing administrator-protected HostExec runtime/configuration',
        'data_permissions': 'Only the actual limited owner execution identity, SYSTEM and Administrators; no dispatcher write access',
        'atomicity': 'One no-replace ledger publication while task disabled; durable journal coordinates separate task/config changes',
        'steps': [
            'Verify current task/process/ledger bindings, strict namespace and sidecars without changing live state',
            'Review exact code/config/task hashes, private data permissions, consistent backup and rollback',
            'Obtain owner approval for the exact cutover; this plan grants none',
            'Under approved scope acquire namespace and exact helper/controller ledger binding before writer lock',
            'Retain writer lock and record one shutdown intent; uncertain outcome holds all later steps',
            'Confirm exact process exit, disable task and verify zero instances',
            'Create only the approved private target; an existing target/stage/journal requires reconciliation',
            'Produce consistent verified backup and copy control ledger to the fresh fixed staging file',
            'Verify staged physical identity, SHA-256, schema/counts and private security before no-replace publication',
            'Apply only reviewed protected code/config and retarget the still-disabled task; retain originals',
            'Verify cutover and durable commit before any separately authorized single start',
        ],
        'rollback_requires': [
            'Known inactive process, disabled task and zero instances',
            'Exact retained old/new code/config/task/security pins and consistent database evidence',
            'No activity in new ledger; otherwise preserve both and reconcile instead of replacing records',
            'No uncertain shutdown, partial migration or unverified journal state',
        ],
        'rollback': 'Restore reviewed old task/config only while inactive; preserve both ledgers, staged files and logs. Archive only separately verified obsolete artifacts; never delete them.',
    }
