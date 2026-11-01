import pytest

from autumn.setup.shortcut import create_shortcut


def test_clickable_launcher_is_created_without_running_its_target(tmp_path):
    from win32com.client.dynamic import Dispatch

    executable=tmp_path/'Autumn.exe'
    executable.write_bytes(b'public nonexecutable test fixture')
    link=create_shortcut(executable,tmp_path/'Autumn.lnk')
    stored=Dispatch('WScript.Shell').CreateShortcut(str(link))
    assert stored.TargetPath.casefold()==str(executable).casefold()
    assert stored.Arguments==''
    assert create_shortcut(executable,link)==link
    other=tmp_path/'other.exe'
    other.write_bytes(b'public nonexecutable test fixture')
    before=link.read_bytes()
    with pytest.raises(ValueError):
        create_shortcut(other,link)
    assert link.read_bytes()==before
