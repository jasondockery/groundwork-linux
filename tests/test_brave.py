"""Brave installer fixtures. Package managers, sudo, and xdg-settings are stubs.

Protects: official repo lines per family, skip rules, deferred installs, default
offer, Chrome notice, and policy JSON rendered from core.
Boundary: the install-brave.sh process, with hostile command stand-ins.
Distinct value: FreeTube tests do not cover Brave, sudo, or the core spec.
"""
import json
import os
from pathlib import Path
import pty
import select
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

REPO = Path(__file__).resolve().parents[1]
CORE_SHA = '0395895c86ed24d942c3803c521cf2131cfa52c7'
KEY_URL = 'https://brave-browser-apt-release.s3.brave.com/brave-browser-archive-keyring.gpg'
SOURCES_URL = 'https://brave-browser-apt-release.s3.brave.com/brave-browser.sources'
RPM_URL = 'https://brave-browser-rpm-release.s3.brave.com/brave-browser.repo'
DESKTOP_ID = 'brave-browser.desktop'
BITWARDEN = 'nngceckbapebfimnlniiiahkandclblb'
SCRIPT = REPO / 'install-brave.sh'
STUB = r'''#!/usr/bin/python3
import json, os, pathlib, shutil, sys
root = pathlib.Path(os.environ['WRAPPER_FIXTURE'])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / 'calls').open('a') as log:
    log.write(json.dumps([name, *args]) + '\n')

def ensure_binary():
    path = pathlib.Path(os.environ['GROUNDWORK_ROOT']) / 'usr/bin/brave-browser'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('#!/bin/sh\n')
    path.chmod(0o755)

def ensure_repo(relative):
    path = pathlib.Path(os.environ['GROUNDWORK_ROOT']) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text('repo\n')

if name == 'uname':
    print(os.environ.get('FIXTURE_OS', 'Linux') if args == ['-s'] else 'unexpected')
elif name == 'sudo':
    body = list(args)
    noninteractive = False
    if body and body[0] == '-n':
        noninteractive = True
        body = body[1:]
        if os.environ.get('FIXTURE_SUDO_NONINTERACTIVE') != '1':
            raise SystemExit(1)
    if os.environ.get('FIXTURE_SUDO_PASSWORD') == '1' and not noninteractive:
        unlocked = root / 'sudo-unlocked'
        if not unlocked.exists():
            print('Password:', flush=True)
            if sys.stdin.readline().strip() != 'secret':
                raise SystemExit(1)
            unlocked.write_text('yes\n')
    while body and '=' in body[0] and not body[0].startswith('-'):
        body = body[1:]
    if body == ['true']:
        raise SystemExit(0)
    if body[:1] == ['install']:
        flags, paths, index = [], [], 1
        while index < len(body):
            token = body[index]
            if token in ('-D', '-d'):
                flags.append(token)
                index += 1
            elif token in ('-o', '-g', '-m'):
                index += 2
            else:
                paths.append(token)
                index += 1
        if '-d' in flags:
            for path in paths:
                pathlib.Path(path).mkdir(parents=True, exist_ok=True)
            raise SystemExit(0)
        dest = pathlib.Path(paths[-1])
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(paths[-2], dest)
        raise SystemExit(0)
    if body[:1] == ['curl']:
        dest = url = None
        index = 1
        while index < len(body):
            token = body[index]
            if token == '--max-time':
                index += 2
                continue
            if token == '-fsSLo':
                dest = body[index + 1]
                index += 2
                continue
            if token.startswith('https://'):
                url = token
            index += 1
        pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(dest).write_text(url + '\n')
        raise SystemExit(0)
    if body[:1] == ['apt']:
        if 'install' in body:
            ensure_binary()
        elif body[1:2] != ['update']:
            raise SystemExit('unexpected apt')
        raise SystemExit(0)
    if body[:1] == ['dnf']:
        if 'addrepo' in body or '--add-repo' in body:
            ensure_repo('etc/yum.repos.d/brave-browser.repo')
            raise SystemExit(0)
        if 'install' in body:
            ensure_binary()
            raise SystemExit(0)
        raise SystemExit('unexpected dnf')
    if body[:1] == ['zypper']:
        if 'addrepo' in body:
            ensure_repo('etc/zypp/repos.d/brave-browser.repo')
            raise SystemExit(0)
        if 'install' in body:
            ensure_binary()
            raise SystemExit(0)
        raise SystemExit('unexpected zypper')
    raise SystemExit('unexpected sudo')
elif name == 'xdg-settings':
    state = root / 'default-browser'
    if args[:2] == ['get', 'default-web-browser']:
        if state.exists():
            print(state.read_text().strip())
        else:
            print(os.environ.get('FIXTURE_DEFAULT_BROWSER', ''))
    elif args[:2] == ['set', 'default-web-browser']:
        state.write_text(args[2] + '\n')
    else:
        raise SystemExit('unexpected xdg-settings')
elif name == 'flatpak':
    if args[:2] == ['info', 'com.brave.Browser']:
        raise SystemExit(0 if (root / 'flatpak-brave').exists() else 1)
    raise SystemExit('unexpected flatpak')
elif name == 'snap':
    if args[:2] == ['list', 'brave']:
        raise SystemExit(0 if (root / 'snap-brave').exists() else 1)
    raise SystemExit('unexpected snap')
elif name in ('yay', 'paru', 'pikaur'):
    if args == ['-Sy', '--noconfirm', 'brave-bin']:
        ensure_binary()
        raise SystemExit(0)
    raise SystemExit('unexpected aur helper')
else:
    raise SystemExit('unexpected command')
'''


def applicable_policies(spec):
    extensions = spec.get('extensions') or []
    bitwarden = any(item.get('id') == BITWARDEN for item in extensions)
    rendered = {}
    for entry in spec['policies']:
        if entry['value'] == entry['upstreamDefault']:
            continue
        condition = entry.get('when')
        if condition == 'Bitwarden is the password manager.' and not bitwarden:
            continue
        if condition not in (None, 'Bitwarden is the password manager.'):
            raise AssertionError(condition)
        rendered[entry['name']] = entry['value']
    return rendered


class BraveInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='groundwork-brave-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        stub = self.bin / 'stub'
        stub.write_text(STUB)
        stub.chmod(0o755)
        for name in ('uname', 'sudo', 'xdg-settings', 'flatpak', 'snap'):
            (self.bin / name).symlink_to(stub)
        for name in ('grep', 'head', 'bash', 'python3', 'mktemp', 'cmp', 'rm', 'mkdir', 'dirname'):
            (self.bin / name).symlink_to(shutil.which(name))
        self.os_release = self.root / 'os-release'
        self.write_os_release(ID='ubuntu', VERSION_ID='"24.04"', ID_LIKE='debian')
        (self.root / 'kernel-osrelease').write_text('6.8.0-100-generic\n')
        self.env = dict(os.environ, WRAPPER_FIXTURE=str(self.root),
                        PATH=str(self.bin), HOME=str(self.root),
                        GROUNDWORK_ROOT=str(self.root),
                        GROUNDWORK_OS_RELEASE_FILE=str(self.os_release),
                        GROUNDWORK_OSRELEASE_FILE=str(self.root / 'kernel-osrelease'),
                        GROUNDWORK_OMARCHY_DIR=str(self.root / 'not-omarchy'),
                        GROUNDWORK_OSTREE_FILE=str(self.root / 'no-ostree'),
                        DISPLAY=':0')
        for key in ('WAYLAND_DISPLAY', 'WSL_DISTRO_NAME', 'WSL_INTEROP',
                    'GROUNDWORK_UPDATE_SCOPE', 'XDG_CONFIG_HOME', 'GROUNDWORK_BRAVE_SPEC',
                    'FIXTURE_OS', 'FIXTURE_DEFAULT_BROWSER', 'FIXTURE_SUDO_NONINTERACTIVE',
                    'FIXTURE_SUDO_PASSWORD', 'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
            self.env.pop(key, None)

    def write_os_release(self, **fields):
        self.os_release.write_text(''.join(f'{key}={value}\n' for key, value in fields.items()))

    def calls(self):
        log = self.root / 'calls'
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def sudo_calls(self):
        return [call[1:] for call in self.calls() if call[0] == 'sudo']

    def reset_calls(self):
        log = self.root / 'calls'
        if log.exists():
            log.unlink()

    def reset_install_state(self):
        for path in (self.root / 'usr', self.root / 'etc', self.root / '.config',
                     self.root / 'calls', self.root / 'default-browser', self.root / 'sudo-unlocked'):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    def policy_path(self):
        return self.root / 'etc' / 'brave' / 'policies' / 'managed' / 'groundwork.json'

    def state_path(self, name):
        return self.root / '.config' / 'groundwork' / name

    def extension_path(self):
        return self.root / 'usr' / 'share' / 'chromium' / 'extensions' / f'{BITWARDEN}.json'

    def run_script(self, *args, status=0):
        result = subprocess.run(['/usr/bin/bash', str(SCRIPT), *args], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, status, result.stdout + result.stderr)
        return result

    def run_pty(self, replies, status=0, args=()):
        pid, fd = pty.fork()
        if pid == 0:
            os.execvpe('/usr/bin/bash', ['bash', str(SCRIPT), *args], self.env)
            os._exit(127)
        buffer = b''
        transcript = b''
        pending = list(replies)
        reaped = None
        deadline = time.time() + 8
        try:
            while time.time() < deadline:
                if pending and pending[0][0] in buffer:
                    marker, answer = pending.pop(0)
                    index = buffer.index(marker)
                    transcript += buffer[:index + len(marker)]
                    buffer = buffer[index + len(marker):]
                    if answer == 'CTRL-C':
                        os.write(fd, b'\x03')
                    elif answer == 'EOF':
                        # VEOF on an empty line is end of file. Closing the
                        # master instead sends SIGHUP and kills the script.
                        os.write(fd, b'\x04')
                    else:
                        os.write(fd, (answer + '\n').encode())
                ready, _, _ = select.select([fd], [], [], 0.2)
                if not ready:
                    result = os.waitpid(pid, os.WNOHANG)
                    if result[0] != 0:
                        reaped = result
                        break
                    continue
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                buffer += chunk
            else:
                os.killpg(pid, signal.SIGKILL)
            if reaped is None:
                reaped = os.waitpid(pid, 0)
            code = os.waitstatus_to_exitcode(reaped[1])
        finally:
            if fd >= 0:
                os.close(fd)
        transcript += buffer
        text = transcript.decode(errors='replace')
        self.assertEqual(pending, [], text)
        self.assertEqual(code, status, text)
        return text

    def test_core_submodule_is_groundwork_core_v070(self):
        env = os.environ.copy()
        for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
            env.pop(key, None)
        sha = subprocess.run(['git', '-C', str(REPO / 'core'), 'rev-parse', 'HEAD'],
                             check=True, capture_output=True, text=True, env=env).stdout.strip()
        self.assertEqual(sha, CORE_SHA)
        self.assertTrue((REPO / 'core' / 'browser' / 'brave.json').is_file())

    def test_help_and_invalid_input_have_no_external_effects(self):
        self.run_script('--help')
        self.run_script('-h')
        self.run_script('--typo', status=64)
        self.run_script('install', status=64)
        self.assertEqual(self.calls(), [])
        self.assertFalse(self.policy_path().exists())
        self.assertFalse(self.state_path('brave-installed').exists())

    def test_other_os_omarchy_wsl_and_headless_skip_before_install(self):
        self.env['FIXTURE_OS'] = 'Darwin'
        result = self.run_script(status=1)
        self.assertIn('on Linux', result.stderr)
        self.env['FIXTURE_OS'] = 'Linux'
        (self.bin / 'omarchy').symlink_to(self.bin / 'stub')
        result = self.run_script(status=1)
        self.assertIn('Omarchy', result.stderr)
        (self.bin / 'omarchy').unlink()
        share = self.root / 'omarchy-share'
        share.mkdir()
        self.env['GROUNDWORK_OMARCHY_DIR'] = str(share)
        result = self.run_script(status=1)
        self.assertIn('Omarchy', result.stderr)
        self.env['GROUNDWORK_OMARCHY_DIR'] = str(self.root / 'not-omarchy')
        (self.root / 'kernel-osrelease').write_text('6.6.87.2-microsoft-standard-WSL2\n')
        result = self.run_script()
        self.assertIn('skipping Brave on WSL', result.stdout)
        self.env.pop('DISPLAY')
        (self.root / 'kernel-osrelease').write_text('6.8.0-100-generic\n')
        result = self.run_script()
        self.assertIn('headless', result.stdout)
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse(self.policy_path().exists())

    def test_no_terminal_defers_and_does_not_record_done(self):
        result = self.run_script()
        self.assertIn('no terminal', result.stdout)
        self.assertIn('retry', result.stdout)
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        self.assertFalse(self.policy_path().exists())
        self.assertFalse(self.state_path('brave-installed').exists())
        self.assertFalse(self.state_path('brave-default-declined').exists())

    def test_debian_family_writes_the_brave_keyring_and_sources(self):
        for fields in (
            {'ID': 'ubuntu', 'VERSION_ID': '"24.04"', 'ID_LIKE': 'debian'},
            {'ID': 'linuxmint', 'VERSION_ID': '"22.1"', 'ID_LIKE': 'ubuntu'},
            {'ID': 'debian', 'VERSION_ID': '"12"'},
        ):
            with self.subTest(fields=fields):
                self.reset_install_state()
                self.write_os_release(**fields)
                self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'n')])
                key = str(self.root / 'usr/share/keyrings/brave-browser-archive-keyring.gpg')
                sources = str(self.root / 'etc/apt/sources.list.d/brave-browser-release.sources')
                self.assertIn(['curl', '--max-time', '60', '-fsSLo', key, KEY_URL], self.sudo_calls())
                self.assertIn(['curl', '--max-time', '60', '-fsSLo', sources, SOURCES_URL], self.sudo_calls())
                self.assertIn(['DEBIAN_FRONTEND=noninteractive', 'apt', 'install', '-y', 'brave-browser'],
                              self.sudo_calls())
                self.assertEqual((self.root / 'usr/share/keyrings/brave-browser-archive-keyring.gpg').read_text().strip(), KEY_URL)

    def test_fedora_rhel_and_opensuse_write_the_brave_repo(self):
        cases = (
            ({'ID': 'fedora', 'VERSION_ID': '41'},
             ['dnf', 'config-manager', 'addrepo', f'--from-repofile={RPM_URL}']),
            ({'ID': 'fedora', 'VERSION_ID': '40'},
             ['dnf', 'config-manager', '--add-repo', RPM_URL]),
            ({'ID': 'rhel', 'VERSION_ID': '"9.4"', 'ID_LIKE': 'fedora'},
             ['dnf', 'config-manager', '--add-repo', RPM_URL]),
            ({'ID': 'opensuse-tumbleweed', 'ID_LIKE': '"suse opensuse"'},
             ['zypper', 'addrepo', RPM_URL]),
        )
        for fields, expected in cases:
            with self.subTest(fields=fields):
                self.reset_install_state()
                self.write_os_release(**fields)
                self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'n')])
                binary = self.root / 'usr' / 'bin' / 'brave-browser'
                self.assertIn(expected, self.sudo_calls())
                self.assertTrue(binary.exists())

    def test_arch_uses_an_aur_helper_or_prints_the_command(self):
        self.write_os_release(ID='arch')
        missing = self.run_script()
        self.assertIn('yay -Sy brave-bin', missing.stdout)
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        (self.bin / 'yay').symlink_to(self.bin / 'stub')
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'n')])
        self.assertIn(['yay', '-Sy', '--noconfirm', 'brave-bin'], self.calls())
        self.assertNotIn('paru', [call[0] for call in self.calls()])

    def test_atomic_and_unknown_families_install_nothing(self):
        self.write_os_release(ID='fedora', VERSION_ID='41', VARIANT_ID='silverblue')
        atomic = self.run_script()
        self.assertIn('rpm-ostree install brave-browser', atomic.stdout)
        self.assertIn(RPM_URL, atomic.stdout)
        self.assertIn('did not change this system', atomic.stdout)
        self.write_os_release(ID='alpine', VERSION_ID='3.20')
        unknown = self.run_script()
        self.assertIn('https://brave.com/linux/', unknown.stdout)
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse(any(call[0] == 'rpm-ostree' for call in self.calls()))
        self.assertFalse(self.policy_path().exists())

    def test_policy_matches_core_and_a_second_run_is_idempotent(self):
        spec = json.loads((REPO / 'core' / 'browser' / 'brave.json').read_text())
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'n')])
        written = json.loads(self.policy_path().read_text())
        self.assertEqual(written, applicable_policies(spec))
        self.assertIn('BraveAIChatEnabled', written)
        self.assertIn('BraveLocalAIEnabled', written)
        self.assertFalse(written['BraveAIChatEnabled'])
        self.assertFalse(written['BraveLocalAIEnabled'])
        self.assertNotIn('ExtensionInstallForcelist', written)
        self.assertNotIn('reason', self.policy_path().read_text())
        policy_writes = [call for call in self.sudo_calls()
                         if call[:2] == ['install', '-D'] and '0644' in call and 'root' in call
                         and str(self.policy_path()) in call]
        self.assertEqual(len(policy_writes), 1)
        first_bytes = self.policy_path().read_bytes()
        apt_installs = [call for call in self.sudo_calls() if 'apt' in call and 'install' in call]
        self.reset_calls()
        second = self.run_script()
        self.assertIn('policies match', second.stdout)
        self.assertEqual(self.policy_path().read_bytes(), first_bytes)
        self.assertEqual([call for call in self.sudo_calls() if 'apt' in call and 'install' in call], [])
        self.assertEqual(apt_installs[0][-1], 'brave-browser')
        self.assertFalse(self.extension_path().exists())

    def test_rows_matching_upstream_and_unmet_conditions_are_omitted(self):
        spec = {
            'schemaVersion': 1,
            'default': {'id': 'brave', 'channel': 'release',
                        'desktopIds': {'linux': DESKTOP_ID}},
            'policies': [
                {'name': 'Keep', 'value': True, 'upstreamDefault': False, 'reason': 'differs'},
                {'name': 'Drop', 'value': True, 'upstreamDefault': True, 'reason': 'matches upstream'},
                {'name': 'PasswordManagerEnabled', 'value': False, 'upstreamDefault': True,
                 'when': 'Bitwarden is the password manager.', 'reason': 'no Bitwarden in this fixture'},
            ],
            'extensions': [],
        }
        path = self.root / 'fixture-spec.json'
        path.write_text(json.dumps(spec))
        self.env['GROUNDWORK_BRAVE_SPEC'] = str(path)
        self.env['FIXTURE_SUDO_NONINTERACTIVE'] = '1'
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        binary = self.root / 'usr' / 'bin' / 'brave-browser'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\n')
        binary.chmod(0o755)
        self.run_script()
        self.assertEqual(json.loads(self.policy_path().read_text()), {'Keep': True})

    def test_unsupported_spec_writes_nothing(self):
        spec = {
            'schemaVersion': 1,
            'default': {'id': 'brave', 'channel': 'release',
                        'desktopIds': {'linux': DESKTOP_ID}},
            'policies': [
                {'name': 'X', 'value': True, 'upstreamDefault': False,
                 'when': 'always', 'reason': 'unsupported'},
            ],
            'extensions': [],
        }
        path = self.root / 'bad-spec.json'
        path.write_text(json.dumps(spec))
        self.env['GROUNDWORK_BRAVE_SPEC'] = str(path)
        result = self.run_script(status=1)
        self.assertIn('unsupported', result.stderr)
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse(self.policy_path().exists())
        self.env['GROUNDWORK_BRAVE_SPEC'] = str(self.root / 'missing-spec.json')
        self.run_script(status=1)

    def test_default_offer_accepted_declined_and_notice(self):
        accepted = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'y')])
        self.assertIn('now the default browser', accepted)
        self.assertIn(['set', 'default-web-browser', DESKTOP_ID],
                      [call[1:] for call in self.calls() if call[0] == 'xdg-settings'])
        self.root.joinpath('default-browser').write_text('firefox.desktop\n')
        self.reset_calls()
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        notice = self.run_script()
        self.assertEqual(notice.stdout.count('Brave is not the default browser'), 1)
        self.assertIn('xdg-settings set default-web-browser brave-browser.desktop', notice.stdout)
        self.assertNotIn(['set', 'default-web-browser', DESKTOP_ID],
                         [call[1:] for call in self.calls() if call[0] == 'xdg-settings'])
        self.env.pop('GROUNDWORK_UPDATE_SCOPE')
        self.env['DISPLAY'] = ':0'
        self.root.joinpath('default-browser').unlink()
        declined = self.run_pty([(b'[y/N]', 'n')])
        self.assertIn('will not ask again', declined)
        self.assertTrue(self.state_path('brave-default-declined').is_file())
        self.reset_calls()
        again = self.run_pty([])
        self.assertNotIn('[y/N]', again)
        self.assertEqual([call for call in self.calls() if call[0] == 'xdg-settings' and call[1] == 'set'], [])

    def test_extension_offer_is_written_only_after_yes(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'y'), (b'[y/N]', 'n')])
        payload = json.loads(self.extension_path().read_text())
        self.assertEqual(payload, {'external_update_url': 'https://clients2.google.com/service/update2/crx'})
        writes = [call for call in self.sudo_calls()
                  if str(self.extension_path()) in call and '0644' in call and 'root' in call]
        self.assertEqual(len(writes), 1)
        self.assertTrue(self.state_path('brave-extension-accepted').is_file())

    def test_chrome_notice_removes_nothing(self):
        chrome = self.bin / 'google-chrome'
        chrome.write_text('#!/bin/sh\nexit 0\n')
        chrome.chmod(0o755)
        chromium = self.bin / 'chromium-browser'
        chromium.write_text('#!/bin/sh\nexit 0\n')
        chromium.chmod(0o755)
        result = self.run_script()
        self.assertIn('brave://settings/importData', result.stdout)
        self.assertIn('will not remove', result.stdout)
        self.assertEqual(self.sudo_calls(), [])
        for call in self.calls():
            self.assertNotIn('uninstall', call)
            self.assertNotIn('purge', call)
            self.assertNotIn('remove', call)

    def test_flatpak_move_is_offered_and_does_not_delete_data(self):
        (self.root / 'flatpak-brave').write_text('present\n')
        data = self.root / 'flatpak-data'
        data.mkdir()
        (data / 'profile').write_text('keep\n')
        declined = self.run_pty([(b'[y/N]', 'n')])
        self.assertIn('keep that data directory', declined.lower())
        self.assertTrue(self.state_path('brave-repo-move-declined').is_file())
        self.assertEqual((data / 'profile').read_text(), 'keep\n')
        self.assertFalse(any('uninstall' in call or 'remove' in call for call in self.calls()))
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        self.state_path('brave-repo-move-declined').unlink()
        self.reset_calls()
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'n')])
        self.assertTrue((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        self.assertEqual((data / 'profile').read_text(), 'keep\n')
        self.assertFalse(any('uninstall' in call for call in self.calls()))

    def test_configuration_keeps_an_installed_brave_and_maintenance_can_install(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'n')])
        self.reset_calls()
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'configuration'
        kept = self.run_script()
        self.assertIn('keeping the installed Brave', kept.stdout)
        self.assertEqual([call for call in self.sudo_calls() if 'apt' in call], [])
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        self.env['FIXTURE_SUDO_NONINTERACTIVE'] = '1'
        binary = self.root / 'usr' / 'bin' / 'brave-browser'
        binary.unlink()
        self.policy_path().unlink()
        self.reset_calls()
        installed = self.run_script()
        self.assertIn('Installed Brave', installed.stdout)
        self.assertTrue(binary.exists())
        self.assertTrue(self.policy_path().exists())
        self.assertNotIn('[y/N]', installed.stdout + installed.stderr)

    def test_prompt_eof_invalid_entry_and_ctrl_c(self):
        eof = self.run_pty([(b'[y/N]', 'EOF')])
        self.assertIn('left unchanged', eof)
        self.assertFalse(self.policy_path().exists())
        self.assertFalse(self.state_path('brave-default-declined').exists())
        invalid = self.run_pty([(b'[y/N]', 'maybe'), (b'[y/N]', 'n')])
        self.assertIn('Enter y or n.', invalid)
        self.assertFalse(self.policy_path().exists())
        self.run_pty([(b'[y/N]', 'CTRL-C')], status=130)
        self.assertFalse(self.policy_path().exists())
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-browser').exists())

    def test_sudo_password_prompt_is_announced_before_sudo_reads(self):
        self.env['FIXTURE_SUDO_PASSWORD'] = '1'
        text = self.run_pty([
            (b'[y/N]', 'y'),
            (b'Password:', 'secret'),
            (b'[y/N]', 'n'),
            (b'[y/N]', 'n'),
        ])
        self.assertLess(text.index('if sudo asks for a password'), text.index('Password:'))
        self.assertTrue(self.policy_path().exists())

    def test_hook_runs_brave_and_keeps_freetube_failure(self):
        hook = REPO / 'engine-hooks/run_after_33-groundwork-linux-desktop-apps.sh'
        freetube = self.root / 'freetube.sh'
        freetube.write_text('#!/bin/bash\nprintf "freetube %s\\n" "$*"\nexit 1\n')
        freetube.chmod(0o755)
        self.env['GROUNDWORK_LINUX_DESKTOP_APPS'] = str(freetube)
        self.env['GROUNDWORK_LINUX_BRAVE'] = str(SCRIPT)
        (self.root / 'kernel-osrelease').write_text('6.6.87.2-microsoft-standard-WSL2\n')
        result = subprocess.run(['/usr/bin/bash', str(hook)], env=self.env,
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('freetube', result.stdout)
        self.assertIn('skipping Brave on WSL', result.stdout)
        self.assertEqual(self.sudo_calls(), [])


if __name__ == '__main__':
    unittest.main()
