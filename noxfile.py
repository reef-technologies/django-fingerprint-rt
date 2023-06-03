import nox
from pathlib import Path


ROOT = Path('.')
PYTHON_VERSIONS = ['3.9', '3.10'][::-1]
DJANGO_VERSIONS = ['3.2', '4.0', '4.1', '4.2'][::-1]
DEMO_APP_DIR = ROOT / 'demo'
TEST_REQUIREMENTS = [
    '.',
    'pytest', 'pytest-django',
    'ipdb', 'freezegun',
    'psycopg2-binary',
    'django-debug-toolbar',
]

nox.options.default_venv_backend = 'venv'
nox.options.stop_on_first_error = True
nox.options.reuse_existing_virtualenvs = True


@nox.session(python=PYTHON_VERSIONS)
def lint(session):
    session.install('flake8', 'mypy', 'django-stubs', 'types-requests', '.')
    session.run('flake8', '--ignore', 'E501', str(DEMO_APP_DIR))
    session.run('mypy', str(DEMO_APP_DIR))


@nox.session(python=PYTHON_VERSIONS)
@nox.parametrize('django', DJANGO_VERSIONS)
def test(session, django: str):
    session.install(f'django~={django}.0', *TEST_REQUIREMENTS)
    session.run('pytest', '-W', 'ignore::DeprecationWarning', '-s', '-vv', str(DEMO_APP_DIR / 'demo' / 'tests'), *session.posargs, env={'DJANGO_SETTINGS_MODULE': 'demo.settings'})
