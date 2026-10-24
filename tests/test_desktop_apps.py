"""FreeTube Flatpak fixtures. Successful installs use a stub flatpak, not the host."""
import os
from pathlib import Path
import subprocess
import tempfile
import json
import unittest

REPO = Path(__file__).resolve().parents[1]
APP_ID = 'io.freetubeapp.FreeTube'
FLATHUB = 'https://dl.flathub.org/repo/flathub.flatpakrepo'
STUB = '''#!/usr/bin/env python3
import os, pathlib, sys
root = pathlib.Path(os.environ['WRAPPER_FIXTURE'])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / 'calls').open('a') as log:
    log.write(__import__('json').dumps([name, *args]) + '\\n')
if name == 'uname':
    print(os.environ.get('FIXTURE_OS', 'Linux') if args == ['-s'] else 'unexpected')
elif name == 'flatpak':
    state = root / 'freetube-installed'
    if os.environ.get('FIXTURE_FLATPAK_FAIL') == (args[0] if args else ''):
        raise SystemExit(1)
    if args[:1] == ['info']:
        raise SystemExit(0 if state.exists() else 1)
    if args[:1] == ['install']:
        state.write_text('installed')
    elif args[:1] not in (['update'], ['remote-add']):
        raise SystemExit('Unexpected flatpak command')
else:
    raise SystemExit('Unexpected command')
'''


class DesktopAppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='groundwork-desktop-apps-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        stub = self.bin / 'stub'
        stub.write_text(STUB)
        stub.chmod(0o755)
        for name in ('uname', 'flatpak'):
            (self.bin / name).symlink_to(stub)
        osrelease = self.root / 'osrelease'
        osrelease.write_text('6.8.0-100-generic\n')
        self.env = dict(os.environ, WRAPPER_FIXTURE=str(self.root),
                        PATH=f'{self.bin}:/usr/bin:/bin', HOME=str(self.root),
                        GROUNDWORK_OSRELEASE_FILE=str(osrelease))
        for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'WSL_DISTRO_NAME', 'WSL_INTEROP',
                    'GROUNDWORK_UPDATE_SCOPE', 'XDG_CONFIG_HOME',
                    'GROUNDWORK_LINUX_DESKTOP_APPS', 'FIXTURE_OS', 'FIXTURE_FLATPAK_FAIL'):
            self.env.pop(key, None)

    def run_installer(self, *args, status=0, script=None):
        target = script or (REPO / 'install-desktop-apps.sh')
        result = subprocess.run(['bash', str(target), *args], env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def calls(self):
        log = self.root / 'calls'
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def flatpak_calls(self):
        return [call[1:] for call in self.calls() if call[0] == 'flatpak']

    def write_headless(self, value):
        config = self.root / '.config' / 'chezmoi'
        config.mkdir(parents=True)
        (config / 'chezmoi.toml').write_text(f'[data]\nname = "Ada"\nheadless = {value}\n')

    def assert_no_freetube_config(self):
        self.assertFalse((self.root / '.var').exists())

    def test_shell_syntax(self):
        for name in ('bootstrap.sh', 'install-desktop-apps.sh',
                     'engine-hooks/run_after_33-groundwork-linux-desktop-apps.sh'):
            subprocess.run(['bash', '-n', str(REPO / name)], check=True)

    def test_sources_do_not_write_freetube_settings(self):
        for name in ('install-desktop-apps.sh',
                     'engine-hooks/run_after_33-groundwork-linux-desktop-apps.sh'):
            text = (REPO / name).read_text()
            self.assertNotIn('config/FreeTube', text)
            self.assertNotIn('.var/app', text)

    def test_help_and_invalid_input_have_no_external_effects(self):
        self.run_installer('--help')
        self.run_installer('-h')
        self.run_installer('--typo', status=64)
        self.run_installer('install', status=64)
        self.assertEqual(self.calls(), [])
        self.assert_no_freetube_config()

    def test_other_os_and_omarchy_are_refused_before_flatpak(self):
        self.env['FIXTURE_OS'] = 'Darwin'
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer(status=1)
        self.assertIn('on Linux', result.stderr)
        self.env['FIXTURE_OS'] = 'Linux'
        (self.bin / 'omarchy').symlink_to(self.bin / 'stub')
        result = self.run_installer(status=1)
        self.assertIn('Omarchy', result.stderr)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_no_freetube_config()

    def test_wsl_skips_even_when_a_desktop_session_and_answer_exist(self):
        self.write_headless('false')
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        self.env['DISPLAY'] = ':0'
        (self.root / 'osrelease').write_text('6.6.87.2-microsoft-standard-WSL2\n')
        result = self.run_installer()
        self.assertIn('skipping FreeTube on WSL', result.stdout)
        (self.root / 'osrelease').write_text('6.8.0-100-generic\n')
        self.env['WSL_DISTRO_NAME'] = 'Ubuntu'
        result = self.run_installer()
        self.assertIn('skipping FreeTube on WSL', result.stdout)
        self.assertEqual(self.flatpak_calls(), [])

    def test_headless_answers_and_missing_sessions_skip(self):
        result = self.run_installer()
        self.assertIn('headless', result.stdout)
        self.write_headless('true')
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer()
        self.assertIn('headless', result.stdout)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_no_freetube_config()

    def test_stored_desktop_installs_without_a_graphical_session(self):
        self.write_headless('false # desktop')
        result = self.run_installer()
        self.assertIn(f'installed FreeTube ({APP_ID})', result.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID],
        ])
        self.assert_no_freetube_config()

    def test_graphical_session_installs_then_update_is_idempotent(self):
        self.env['DISPLAY'] = ':1'
        first = self.run_installer()
        self.assertIn('installed FreeTube', first.stdout)
        second = self.run_installer()
        self.assertIn('updated FreeTube', second.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID],
            ['info', '--user', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['update', '--user', '-y', '--noninteractive', APP_ID],
        ])
        self.assert_no_freetube_config()

    def test_configuration_scope_installs_once_and_then_keeps_it(self):
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'configuration'
        first = self.run_installer()
        self.assertIn('installed FreeTube', first.stdout)
        second = self.run_installer()
        self.assertIn('Configuration-only apply', second.stdout)
        self.assertIn('update-all', second.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID],
            ['info', '--user', APP_ID],
        ])

    def test_maintenance_scope_updates_an_existing_install(self):
        (self.root / 'freetube-installed').write_text('installed')
        self.env['DISPLAY'] = ':1'
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        result = self.run_installer()
        self.assertIn('updated FreeTube', result.stdout)
        self.assertEqual(self.flatpak_calls()[-1],
                         ['update', '--user', '-y', '--noninteractive', APP_ID])

    def test_missing_flatpak_on_a_desktop_fails_before_a_config_write(self):
        self.bin.joinpath('flatpak').unlink()
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer(status=1)
        self.assertIn('needs Flatpak', result.stderr)
        self.assertIn('sudo apt install flatpak', result.stderr)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_no_freetube_config()

    def test_flatpak_install_failure_is_returned(self):
        self.env['DISPLAY'] = ':1'
        self.env['FIXTURE_FLATPAK_FAIL'] = 'install'
        result = self.run_installer(status=1)
        self.assertNotIn('installed FreeTube', result.stdout)
        self.assertFalse((self.root / 'freetube-installed').exists())

    def test_engine_hook_requires_the_helper_and_forwards_the_desktop_rules(self):
        hook = REPO / 'engine-hooks/run_after_33-groundwork-linux-desktop-apps.sh'
        missing = self.run_installer(status=1, script=hook)
        self.assertIn('helper is missing', missing.stderr)
        self.env['GROUNDWORK_LINUX_DESKTOP_APPS'] = str(REPO / 'install-desktop-apps.sh')
        (self.root / 'osrelease').write_text('6.6.87.2-microsoft-standard-WSL2\n')
        skipped = self.run_installer(script=hook)
        self.assertIn('skipping FreeTube on WSL', skipped.stdout)
        helped = self.run_installer('--help', script=hook)
        self.assertIn(APP_ID, helped.stdout)
        self.assertEqual(self.flatpak_calls(), [])


if __name__ == '__main__':
    unittest.main()
