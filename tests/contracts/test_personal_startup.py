from test_hands_free import fixtures


def test_startup_is_opt_in_to_real_launch_and_cancel_does_not_rearm():
    vm=fixtures.make_vm()
    try:
        vm.settings=vm.settings.model_copy(update={'broad_open_access':True,'hands_free_on_launch':True})
        vm.launch_tick()
        assert not vm.supervisor.jobs
        vm.launch_services=True
        vm.launch_stage='pending'
        vm.launch_tick()
        assert vm.supervisor.jobs[-1].kind=='activate_model' and vm.supervisor.jobs[-1].start_runtime
        vm.brain_warming=False
        vm.launch_stage='discover'
        vm.launch_tick()
        assert vm.supervisor.jobs[-1].kind=='import_catalog'
        vm.stop()
        vm.brain_warming=False
        vm.launch_tick()
        assert not vm.voice.hands_free
    finally:
        vm.shutdown()


def test_login_startup_honors_the_saved_preference_without_opening_audio():
    vm=fixtures.make_vm()
    try:
        vm.settings=vm.settings.model_copy(update={'hands_free_on_launch':True})
        vm.launch_services=True
        vm.launch_listening=False
        vm.launch_stage='listen'
        vm.launch_tick()
        assert not vm.voice.enabled and not vm.voice.service.sent
    finally:
        vm.shutdown()


def test_personal_startup_primes_speech_without_turning_on_the_microphone():
    vm=fixtures.make_vm()
    try:
        vm.settings=vm.settings.model_copy(update={'hands_free_on_launch':True})
        vm.launch_services=True
        vm.launch_stage='pending'
        vm.launch_tick()
        assert [(role,kind) for role,kind,_ in vm.voice.service.sent]==[('recognition','warm'),('playback','warm')]
        assert not vm.voice.recording and not vm.voice.enabled
    finally:
        vm.shutdown()
