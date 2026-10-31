from test_worker import wait_for

from autumn.actions.routines import Routine
from autumn.actions.schemas import Capabilities
from autumn.controller.contracts import Request
from autumn.controller.worker import Job, Supervisor
from autumn.storage.settings import Settings


def test_saved_routine_restores_and_runs_each_step_with_wake_authority(tmp_path):
    worker=Supervisor(tmp_path)
    try:
        wait_for(worker,'ready')
        routine=Routine(id='test-routine',name='Show local help',steps=(Capabilities(),Capabilities()))
        worker.submit(Job(kind='save_settings',generation=0,settings=Settings(routines=(routine,),model_enabled=False)))
        wait_for(worker,'settings_saved')
    finally:
        assert worker.shutdown()
    worker=Supervisor(tmp_path)
    try:
        ready,_=wait_for(worker,'ready')
        assert ready['settings']['routines'][0]['id']=='test-routine'
        worker.submit(Job(kind='execute',generation=0,request=Request(generation=0,origin='wake_voice'),text='run routine Show local help'))
        _,events=wait_for(worker,'action_finished')
        steps=[e for e in events if e['kind']=='action_result' and e.get('skill')=='help.capabilities']
        assert len(steps)==2 and all(e['outcome']['status']=='succeeded' for e in steps)
        worker.submit(Job(kind='history',generation=0))
        history,_=wait_for(worker,'history')
        assert len(history['rows'])==2 and all(r['origin']=='wake_voice' for r in history['rows'])
    finally:
        assert worker.shutdown()
