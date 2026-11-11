"""EasyEffects Flatpak fixtures. Successful installs use a stub flatpak, not the host."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
APP_ID = 'com.github.wwmm.easyeffects'
FLATHUB = 'https://dl.flathub.org/repo/flathub.flatpakrepo'
STUB = '''#!/usr/bin/python3
import os, pathlib, sys
root = pathlib.Path(os.environ['WRAPPER_FIXTURE'])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / 'calls').open('a') as log:
    log.write(__import__('json').dumps([name, *args]) + '\\n')
if name in ('uname', 'pipewire', 'pw-cli', 'easyeffects'):
    if name == 'uname':
        print(os.environ.get('FIXTURE_OS', 'Linux') if args == ['-s'] else 'unexpected')
elif name == 'flatpak':
    user_state = root / 'easyeffects-user'
    system_state = root / 'easyeffects-system'
    if os.environ.get('FIXTURE_FLATPAK_FAIL') == (args[0] if args else ''):
        raise SystemExit(1)
    if args[:1] == ['info']:
        scope = 'user'
        if len(args) > 1 and args[1] == '--system':
            scope = 'system'
        elif len(args) > 1 and args[1] == '--user':
            scope = 'user'
        present = user_state if scope == 'user' else system_state
        raise SystemExit(0 if present.exists() else 1)
    if args[:1] == ['install']:
        user_state.write_text('installed')
    elif args[:1] not in (['update'], ['remote-add']):
        raise SystemExit('Unexpected flatpak command')
else:
    raise SystemExit('Unexpected command')
'''


class EasyEffectsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='groundwork-easyeffects-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        stub = self.bin / 'stub'
        stub.write_text(STUB)
        stub.chmod(0o755)
        for name in ('uname', 'flatpak', 'pipewire'):
            (self.bin / name).symlink_to(stub)
        for name in ('grep', 'head', 'bash', 'python3'):
            (self.bin / name).symlink_to(shutil.which(name))
        osrelease = self.root / 'osrelease'
        osrelease.write_text('6.8.0-100-generic\n')
        self.env = dict(os.environ, WRAPPER_FIXTURE=str(self.root),
                        PATH=str(self.bin), HOME=str(self.root),
                        GROUNDWORK_OSRELEASE_FILE=str(osrelease),
                        GROUNDWORK_OMARCHY_DIR=str(self.root / 'not-omarchy'))
        for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'WSL_DISTRO_NAME', 'WSL_INTEROP',
                    'GROUNDWORK_UPDATE_SCOPE', 'XDG_CONFIG_HOME',
                    'GROUNDWORK_LINUX_DESKTOP_APPS', 'GROUNDWORK_LINUX_BRAVE',
                    'GROUNDWORK_LINUX_EASYEFFECTS', 'FIXTURE_OS', 'FIXTURE_FLATPAK_FAIL'):
            self.env.pop(key, None)

    def run_installer(self, *args, status=0, script=None):
        target = script or (REPO / 'install-easyeffects.sh')
        result = subprocess.run(['/usr/bin/bash', str(target), *args], env=self.env,
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

    def plant_config(self):
        native = self.root / '.config' / 'easyeffects'
        native.mkdir(parents=True)
        (native / 'config.json').write_text('{"owned": true}\n')
        flatpak = self.root / '.var' / 'app' / APP_ID / 'config' / 'easyeffects'
        flatpak.mkdir(parents=True)
        (flatpak / 'config.json').write_text('{"owned": true}\n')
        return native / 'config.json', flatpak / 'config.json'

    def assert_config_untouched(self, native=None, flatpak=None):
        if native is None and flatpak is None:
            self.assertFalse((self.root / '.config' / 'easyeffects').exists())
            self.assertFalse((self.root / '.var').exists())
            return
        self.assertEqual(native.read_text(), '{"owned": true}\n')
        self.assertEqual(flatpak.read_text(), '{"owned": true}\n')

    def assert_flatpak_failure_continues(self, result):
        self.assertIn("wasn't installed or updated", result.stderr)
        self.assertIn('rest of the apply continues', result.stderr)
        self.assertIn('update-all', result.stderr)
        self.assertIn('retry', result.stderr)
        self.assertNotIn('installed EasyEffects', result.stdout)
        self.assertNotIn('updated EasyEffects', result.stdout)

    def reset_calls(self):
        log = self.root / 'calls'
        if log.exists():
            log.unlink()

    def test_shell_syntax(self):
        subprocess.run(['bash', '-n', str(REPO / 'install-easyeffects.sh')], check=True)

    def test_sources_do_not_write_easyeffects_settings(self):
        text = (REPO / 'install-easyeffects.sh').read_text()
        self.assertNotIn('.config/easyeffects', text)
        self.assertNotIn('.var/app', text)

    def test_help_and_invalid_input_have_no_external_effects(self):
        native, flatpak = self.plant_config()
        helped = self.run_installer('--help')
        self.assertIn('distribution package or system Flatpak', helped.stdout)
        self.run_installer('-h')
        self.run_installer('--typo', status=64)
        self.run_installer('install', status=64)
        self.assertEqual(self.calls(), [])
        self.assert_config_untouched(native, flatpak)

    def test_other_os_and_omarchy_are_refused_before_flatpak(self):
        native, flatpak = self.plant_config()
        self.env['FIXTURE_OS'] = 'Darwin'
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer(status=1)
        self.assertIn('on Linux', result.stderr)
        self.env['FIXTURE_OS'] = 'Linux'
        (self.bin / 'omarchy').symlink_to(self.bin / 'stub')
        result = self.run_installer(status=1)
        self.assertIn('Omarchy', result.stderr)
        share = self.root / 'omarchy-share'
        share.mkdir()
        self.env['GROUNDWORK_OMARCHY_DIR'] = str(share)
        (self.bin / 'omarchy').unlink()
        result = self.run_installer(status=1)
        self.assertIn('Omarchy', result.stderr)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_config_untouched(native, flatpak)

    def test_wsl_skips_even_when_a_desktop_session_and_answer_exist(self):
        native, flatpak = self.plant_config()
        self.write_headless('false')
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        self.env['DISPLAY'] = ':0'
        (self.root / 'osrelease').write_text('6.6.87.2-microsoft-standard-WSL2\n')
        result = self.run_installer()
        self.assertIn('skipping EasyEffects on WSL', result.stdout)
        (self.root / 'osrelease').write_text('6.8.0-100-generic\n')
        self.env['WSL_DISTRO_NAME'] = 'Ubuntu'
        result = self.run_installer()
        self.assertIn('skipping EasyEffects on WSL', result.stdout)
        self.env.pop('WSL_DISTRO_NAME')
        self.env['WSL_INTEROP'] = '/run/WSL/1_interop'
        result = self.run_installer()
        self.assertIn('skipping EasyEffects on WSL', result.stdout)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_config_untouched(native, flatpak)

    def test_headless_answers_and_missing_sessions_skip(self):
        native, flatpak = self.plant_config()
        result = self.run_installer()
        self.assertIn('headless', result.stdout)
        self.write_headless('true')
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer()
        self.assertIn('headless', result.stdout)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_config_untouched(native, flatpak)

    def test_missing_pipewire_skips_without_installing(self):
        native, flatpak = self.plant_config()
        (self.bin / 'pipewire').unlink()
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer()
        self.assertIn('PipeWire is not available', result.stdout)
        self.assertIn('does not support PulseAudio', result.stdout)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_config_untouched(native, flatpak)

    def test_pw_cli_counts_as_pipewire(self):
        (self.bin / 'pipewire').unlink()
        (self.bin / 'pw-cli').symlink_to(self.bin / 'stub')
        self.env['DISPLAY'] = ':1'
        result = self.run_installer()
        self.assertIn(f'installed EasyEffects ({APP_ID})', result.stdout)
        self.assertEqual(self.flatpak_calls()[-1],
                         ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID])

    def test_distribution_package_is_kept(self):
        native, flatpak = self.plant_config()
        (self.bin / 'easyeffects').symlink_to(self.bin / 'stub')
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer()
        self.assertIn('keeping the installed EasyEffects', result.stdout)
        self.assertIn('does not replace a distribution package', result.stdout)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_config_untouched(native, flatpak)

    def test_system_flatpak_is_kept(self):
        native, flatpak = self.plant_config()
        (self.root / 'easyeffects-system').write_text('installed')
        self.env['DISPLAY'] = ':1'
        result = self.run_installer()
        self.assertIn('keeping the installed EasyEffects', result.stdout)
        self.assertIn('does not replace a system Flatpak', result.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['info', '--system', APP_ID],
        ])
        self.assert_config_untouched(native, flatpak)

    def test_stored_desktop_installs_without_a_graphical_session(self):
        native, flatpak = self.plant_config()
        self.write_headless('false # desktop')
        result = self.run_installer()
        self.assertIn(f'installed EasyEffects ({APP_ID})', result.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['info', '--system', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID],
        ])
        self.assert_config_untouched(native, flatpak)

    def test_graphical_session_installs_then_update_is_idempotent(self):
        native, flatpak = self.plant_config()
        self.env['DISPLAY'] = ':1'
        first = self.run_installer()
        self.assertIn('installed EasyEffects', first.stdout)
        second = self.run_installer()
        self.assertIn('updated EasyEffects', second.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['info', '--system', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID],
            ['info', '--user', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['update', '--user', '-y', '--noninteractive', APP_ID],
        ])
        self.assert_config_untouched(native, flatpak)

    def test_configuration_scope_installs_once_and_then_keeps_it(self):
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'configuration'
        first = self.run_installer()
        self.assertIn('installed EasyEffects', first.stdout)
        second = self.run_installer()
        self.assertIn('Configuration-only apply', second.stdout)
        self.assertIn('update-all', second.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['info', '--system', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID],
            ['info', '--user', APP_ID],
        ])
        self.assert_config_untouched()

    def test_maintenance_scope_installs_when_missing_and_updates_when_present(self):
        self.env['DISPLAY'] = ':1'
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        installed = self.run_installer()
        self.assertIn('installed EasyEffects', installed.stdout)
        updated = self.run_installer()
        self.assertIn('updated EasyEffects', updated.stdout)
        self.assertEqual(self.flatpak_calls(), [
            ['info', '--user', APP_ID],
            ['info', '--system', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['install', '--user', '-y', '--noninteractive', 'flathub', APP_ID],
            ['info', '--user', APP_ID],
            ['remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB],
            ['update', '--user', '-y', '--noninteractive', APP_ID],
        ])

    def test_missing_flatpak_on_a_desktop_fails_before_a_config_write(self):
        native, flatpak = self.plant_config()
        self.bin.joinpath('flatpak').unlink()
        self.env['WAYLAND_DISPLAY'] = 'wayland-1'
        result = self.run_installer(status=1)
        self.assertIn('needs Flatpak', result.stderr)
        self.assertIn('sudo apt install flatpak', result.stderr)
        self.assertEqual(self.flatpak_calls(), [])
        self.assert_config_untouched(native, flatpak)

    def test_flatpak_command_failures_continue_the_apply(self):
        self.env['DISPLAY'] = ':1'
        hook = REPO / 'engine-hooks/run_after_33-groundwork-linux-desktop-apps.sh'
        for command in ('remote-add', 'install', 'update'):
            for script in (None, hook):
                with self.subTest(command=command, script=script):
                    self.reset_calls()
                    state = self.root / 'easyeffects-user'
                    if command == 'update':
                        state.write_text('installed')
                    elif state.exists():
                        state.unlink()
                    self.env['FIXTURE_FLATPAK_FAIL'] = command
                    if script is None:
                        self.env.pop('GROUNDWORK_LINUX_EASYEFFECTS', None)
                    else:
                        self.env['GROUNDWORK_LINUX_EASYEFFECTS'] = str(REPO / 'install-easyeffects.sh')
                    result = self.run_installer(script=script)
                    self.assert_flatpak_failure_continues(result)
                    names = [call[0] for call in self.flatpak_calls()]
                    self.assertIn(command, names)
                    if command == 'remote-add':
                        self.assertNotIn('install', names)
                        self.assertNotIn('update', names)
                    if command == 'install':
                        self.assertFalse(state.exists())

    def test_engine_hook_skips_a_missing_helper_and_forwards_desktop_rules(self):
        hook = REPO / 'engine-hooks/run_after_33-groundwork-linux-desktop-apps.sh'
        missing = self.run_installer(script=hook)
        self.assertIn('not executable', missing.stderr)
        self.assertIn('only skips EasyEffects', missing.stderr)
        inert = self.root / 'inert-helper.sh'
        inert.write_text('#!/bin/bash\nexit 7\n')
        inert.chmod(0o644)
        self.env['GROUNDWORK_LINUX_EASYEFFECTS'] = str(inert)
        unexecutable = self.run_installer(script=hook)
        self.assertIn('not executable', unexecutable.stderr)
        self.assertIn('only skips EasyEffects', unexecutable.stderr)
        self.env['GROUNDWORK_LINUX_EASYEFFECTS'] = str(REPO / 'install-easyeffects.sh')
        (self.root / 'osrelease').write_text('6.6.87.2-microsoft-standard-WSL2\n')
        skipped = self.run_installer(script=hook)
        self.assertIn('skipping EasyEffects on WSL', skipped.stdout)
        helped = self.run_installer('--help', script=hook)
        self.assertIn(APP_ID, helped.stdout)
        self.assertEqual(self.flatpak_calls(), [])


if __name__ == '__main__':
    unittest.main()
