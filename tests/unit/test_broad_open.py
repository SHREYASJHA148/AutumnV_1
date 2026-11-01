import pytest

from autumn.actions.broad_open import authorize_discovered, direct_open
from autumn.actions.catalog import AppEntry
from autumn.storage.settings import Settings


def test_discovery_permission_enables_new_apps_preserving_explicit_disable():
    old=AppEntry(id='old',name='Owner app',kind='package',target='Example!App',reviewed=True)
    new=AppEntry(id='new',name='New app',kind='package',target='Other!App')
    apps=authorize_discovered((old,),(old,new),True)
    assert not apps[0].enabled
    assert apps[1].enabled and apps[1].reviewed
    assert not authorize_discovered((),(new,),False)[0].enabled


def test_broad_permission_refreshes_updated_app_metadata_but_preserves_owner_aliases():
    old=AppEntry(id='app',name='My app',aliases=('favorite',),kind='executable',target='C:\\fixture.exe',fingerprint='old',enabled=True,reviewed=True)
    discovered=old.model_copy(update={'name':'Discovered name','fingerprint':'new'})
    refreshed=authorize_discovered((old,),(discovered,),True)[0]
    assert refreshed.fingerprint=='new' and refreshed.name=='My app' and refreshed.aliases==('favorite',)


@pytest.mark.parametrize('folder',[True,False])
def test_explicit_local_path_compiles_to_an_id_without_mutating_settings(tmp_path,folder):
    path=tmp_path/'public file é.txt'
    path.mkdir() if folder else path.write_text('public fixture')
    settings=Settings(broad_open_access=True)
    route,compiled=direct_open('open "'+str(path)+'"',settings)
    assert route.plan is not None
    assert route.plan.steps[0].skill==('folder.open' if folder else 'app.open')
    assert str(path) not in route.plan.model_dump_json()
    assert compiled is not settings
    assert settings.apps==()


def test_direct_path_requires_permission_and_never_accepts_script_or_extra_command(tmp_path):
    script=tmp_path/'danger.ps1'
    script.write_text('public fixture')
    assert direct_open('open '+str(script),Settings())[0] is None
    route,_=direct_open('open '+str(script),Settings(broad_open_access=True))
    assert route.plan is None
    text=tmp_path/'safe.txt'
    text.write_text('public fixture')
    route,_=direct_open('open '+str(text)+' | hidden',Settings(broad_open_access=True))
    assert route.plan is None
