"""Real contained setup process; no downloads and no audio hardware."""
import time

from autumn.controller.worker import Supervisor
from autumn.setup.worker import SetupJob, setup_worker
from autumn.speech.assets import ARTIFACTS


def test_packaging_setup_inventory_missing_assets_is_local_and_repeatable(tmp_path):
    worker = Supervisor(tmp_path,worker_target=setup_worker,owned_job=True)
    try:
        assert worker.submit(SetupJob(kind='inspect',generation=0,root=str(tmp_path/'models é')))
        deadline = time.monotonic()+10
        rows = None
        while time.monotonic()<deadline:
            for event in worker.poll():
                assert event['kind'] not in {'setup_error','worker_failed'}
                if event['kind']=='setup_inventory':
                    rows = event['rows']
            if rows is not None:
                break
            time.sleep(.01)
        assert {r['id'] for r in rows}==set(ARTIFACTS)
        assert all(r['state']=='Missing or needs repair' for r in rows)
        assert not (tmp_path/'models é').exists()
        worker.cancel(1)
        assert worker.submit(SetupJob(kind='inspect',generation=1,root=str(tmp_path/'models é')))
        deadline = time.monotonic()+3
        while time.monotonic()<deadline:
            if any(e['kind']=='setup_inventory' and e['generation']==1 for e in worker.poll()):
                break
            time.sleep(.01)
        else:
            raise AssertionError('Setup failed to accept the next cancellation generation')
    finally:
        assert worker.shutdown()
