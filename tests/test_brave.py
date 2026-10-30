"""Brave installer fixtures. Package managers, sudo, and xdg-settings are stubs.

Protects: official repo lines per family, skip rules, deferred installs, the
once-only automatic default and its launch check, Chrome notice, and policy JSON rendered from core.
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
import json, os, pathlib, shutil, sys, time
root = pathlib.Path(os.environ['WRAPPER_FIXTURE'])
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with (root / 'calls').open('a') as log:
    log.write(json.dumps([name, *args]) + '\n')

def ensure_binary():
    path = pathlib.Path(os.environ['GROUNDWORK_ROOT']) / 'usr/bin/brave-browser'
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = os.environ.get('FIXTURE_BRAVE_MODE', 'ok')
    if mode == 'crash':
        body = 'exit 139\n'
    elif mode == 'hang':
        body = "trap '' TERM\nwhile :; do sleep 1; done\n"
    elif mode == 'badexit':
        body = "trap 'exit 3' TERM\nwhile :; do sleep 1; done\n"
    else:
        body = "trap 'exit 0' TERM\nwhile :; do sleep 1; done\n"
    log = str(path.parent / 'brave-launch.log')
    path.write_text('#!/bin/sh\n{ echo "ARGS $*"; env; } > ' + log + '\n' + body)
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
    if body[:1] == ['rm']:
        for token in body[1:]:
            if token.startswith('-'):
                continue
            path = pathlib.Path(token)
            if path.is_file() or path.is_symlink():
                path.unlink()
        raise SystemExit(0)
    if body[:1] in (['apt'], ['apt-get']):
        if os.environ.get('FIXTURE_APT_CURL_FAIL') == '1' and 'curl' in body:
            raise SystemExit(1)
        if 'install' in body and 'curl' in body and 'brave-browser' not in body:
            bindir = pathlib.Path(os.environ['PATH'].split(':')[0])
            curl = bindir / 'curl'
            if not curl.exists():
                curl.symlink_to(bindir / 'stub')
            raise SystemExit(0)
        if 'install' in body:
            ensure_binary()
        elif body[1:2] != ['update']:
            raise SystemExit('unexpected apt')
        raise SystemExit(0)
    if body[:1] == ['dnf']:
        if 'addrepo' in body or '--add-repo' in body:
            ensure_repo('etc/yum.repos.d/brave-browser.repo')
            raise SystemExit(0)
        if 'install' in body and 'dnf-plugins-core' in body and 'brave-browser' not in body:
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
elif name == 'curl':
    dest = url = None
    index = 0
    while index < len(args):
        token = args[index]
        if token == '--max-time':
            index += 2
            continue
        if token == '-fsSLo':
            dest = args[index + 1]
            index += 2
            continue
        if token.startswith('https://'):
            url = token
        index += 1
    pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)
    (root / 'curl-dest').write_text(dest + '\n')
    if os.environ.get('FIXTURE_CURL_HOLD') == '1':
        pathlib.Path(dest).write_text('short\n')
        print('curl-holding', flush=True)
        time.sleep(30)
        raise SystemExit(0)
    if os.environ.get('FIXTURE_CURL_EXIT') == '28':
        pathlib.Path(dest).write_text('short\n')
        raise SystemExit(28)
    body = os.environ.get('FIXTURE_CURL_BODY', '')
    if body == 'html':
        pathlib.Path(dest).write_text('<html>captive portal</html>\n')
    elif body == 'empty':
        pathlib.Path(dest).write_text('')
    elif url and 'keyring.gpg' in url:
        pathlib.Path(dest).write_text('-----BEGIN PGP PUBLIC KEY BLOCK-----\n')
    elif url and url.endswith('.sources'):
        pathlib.Path(dest).write_text(
            'Signed-By: /usr/share/keyrings/brave-browser-archive-keyring.gpg\n')
    else:
        pathlib.Path(dest).write_text((url or '') + '\n')
    raise SystemExit(0)
elif name == 'gpg':
    if '--show-keys' in args:
        data = pathlib.Path(args[-1]).read_bytes()
        if b'BEGIN PGP PUBLIC KEY BLOCK' in data and b'<html' not in data.lower():
            raise SystemExit(0)
        raise SystemExit(1)
    raise SystemExit('unexpected gpg')
elif name == 'xdg-settings':
    state = root / 'default-browser'
    if args[:2] == ['get', 'default-web-browser']:
        if state.exists():
            print(state.read_text().strip())
        else:
            print(os.environ.get('FIXTURE_DEFAULT_BROWSER', ''))
    elif args[:2] == ['set', 'default-web-browser']:
        if os.environ.get('FIXTURE_XDG_IGNORE_SET') != '1':
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
        for name in ('uname', 'sudo', 'xdg-settings', 'flatpak', 'snap', 'curl', 'gpg'):
            (self.bin / name).symlink_to(stub)
        for name in ('grep', 'head', 'bash', 'python3', 'mktemp', 'cmp', 'rm', 'mkdir', 'dirname', 'env', 'sleep'):
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
                        GROUNDWORK_BRAVE_SETTLE_SECONDS='1', GROUNDWORK_BRAVE_CLOSE_SECONDS='2',
                        DISPLAY=':0')
        for key in ('WAYLAND_DISPLAY', 'WSL_DISTRO_NAME', 'WSL_INTEROP',
                    'GROUNDWORK_UPDATE_SCOPE', 'XDG_CONFIG_HOME', 'GROUNDWORK_BRAVE_SPEC',
                    'FIXTURE_OS', 'FIXTURE_DEFAULT_BROWSER', 'FIXTURE_SUDO_NONINTERACTIVE',
                    'FIXTURE_SUDO_PASSWORD', 'FIXTURE_CURL_EXIT', 'FIXTURE_CURL_HOLD',
                    'FIXTURE_CURL_BODY', 'FIXTURE_APT_CURL_FAIL', 'FIXTURE_BRAVE_MODE', 'FIXTURE_XDG_IGNORE_SET',
                    'GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE'):
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
                key_path = self.root / 'usr/share/keyrings/brave-browser-archive-keyring.gpg'
                key_path.parent.mkdir(parents=True)
                key_path.write_text('stale\n')
                self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
                curl_calls = [call for call in self.calls() if call[0] == 'curl']
                self.assertTrue(any(
                    call[1:4] == ['--max-time', '60', '-fsSLo'] and call[-1] == KEY_URL
                    for call in curl_calls))
                self.assertTrue(any(call[-1] == SOURCES_URL for call in curl_calls))
                self.assertIn(['DEBIAN_FRONTEND=noninteractive', 'apt', 'install', '-y', 'brave-browser'],
                              self.sudo_calls())
                self.assertIn('BEGIN PGP PUBLIC KEY BLOCK', key_path.read_text())
                self.assertNotIn('stale', key_path.read_text())
                sources_path = self.root / 'etc/apt/sources.list.d/brave-browser-release.sources'
                self.assertIn('Signed-By: /usr/share/keyrings/brave-browser-archive-keyring.gpg',
                              sources_path.read_text())

    def test_debian_installs_curl_before_the_keyring_when_curl_is_missing(self):
        (self.bin / 'curl').unlink()
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        apt_curl = key_curl = None
        for index, call in enumerate(self.calls()):
            if call[0] == 'sudo' and 'apt-get' in call and 'curl' in call:
                apt_curl = index
            if call[0] == 'curl' and call[-1] == KEY_URL:
                key_curl = index
                break
        self.assertIsNotNone(apt_curl)
        self.assertIsNotNone(key_curl)
        self.assertLess(apt_curl, key_curl)
        self.assertIn(['DEBIAN_FRONTEND=noninteractive', 'apt-get', 'install', '-y', 'curl'],
                      self.sudo_calls())
        self.assertTrue((self.bin / 'curl').exists())

    def test_curl_install_failure_names_the_apt_command(self):
        (self.bin / 'curl').unlink()
        self.env['FIXTURE_APT_CURL_FAIL'] = '1'
        result = self.run_pty([(b'[y/N]', 'y')])
        self.assertIn('sudo apt install curl', result)
        self.assertEqual([call for call in self.calls() if call[0] == 'curl'], [])
        self.assertFalse((self.root / 'usr/share/keyrings/brave-browser-archive-keyring.gpg').exists())
        self.assertFalse((self.root / 'usr/bin/brave-browser').exists())

    def test_partial_keyring_download_keeps_the_old_file_until_success(self):
        key = self.root / 'usr/share/keyrings/brave-browser-archive-keyring.gpg'
        sources = self.root / 'etc/apt/sources.list.d/brave-browser-release.sources'
        key.parent.mkdir(parents=True)
        sources.parent.mkdir(parents=True)
        key.write_text('good-keyring\n')
        sources.write_text('good-sources\n')
        self.env['FIXTURE_CURL_EXIT'] = '28'
        self.run_pty([(b'[y/N]', 'y')])
        self.assertEqual(key.read_text(), 'good-keyring\n')
        self.assertEqual(sources.read_text(), 'good-sources\n')
        self.assertNotIn('short', key.read_text())
        self.assertNotIn(['rm', '-f', '--', str(key)], self.sudo_calls())
        temp = Path((self.root / 'curl-dest').read_text().strip())
        self.assertNotEqual(temp, key)
        self.assertFalse(temp.exists())
        self.assertFalse((self.root / 'usr/bin/brave-browser').exists())
        self.env.pop('FIXTURE_CURL_EXIT')
        self.reset_calls()
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.assertIn('BEGIN PGP PUBLIC KEY BLOCK', key.read_text())
        self.assertIn('Signed-By: /usr/share/keyrings/brave-browser-archive-keyring.gpg',
                      sources.read_text())
        self.assertTrue((self.root / 'usr/bin/brave-browser').exists())

    def test_ctrl_c_during_download_removes_the_temp_file(self):
        self.env['FIXTURE_CURL_HOLD'] = '1'
        self.run_pty([(b'[y/N]', 'y'), (b'curl-holding', 'CTRL-C')], status=130)
        temp = Path((self.root / 'curl-dest').read_text().strip())
        self.assertIn(os.sep + 'tmp' + os.sep, str(temp))
        self.assertFalse(temp.exists())
        self.assertFalse(temp.parent.exists())
        self.assertFalse((self.root / 'usr/share/keyrings/brave-browser-archive-keyring.gpg').exists())

    def test_unusable_download_does_not_replace_a_keyring(self):
        key = self.root / 'usr/share/keyrings/brave-browser-archive-keyring.gpg'
        sources = self.root / 'etc/apt/sources.list.d/brave-browser-release.sources'
        key.parent.mkdir(parents=True)
        sources.parent.mkdir(parents=True)
        for body in ('html', 'empty'):
            with self.subTest(body=body):
                key.write_text('good-keyring\n')
                sources.write_text('good-sources\n')
                self.env['FIXTURE_CURL_BODY'] = body
                self.reset_calls()
                self.run_pty([(b'[y/N]', 'y')])
                self.assertEqual(key.read_text(), 'good-keyring\n')
                self.assertEqual(sources.read_text(), 'good-sources\n')
                self.assertFalse((self.root / 'usr/bin/brave-browser').exists())
                self.assertFalse(any(
                    call[:2] == ['install', '-D'] and str(key) in call for call in self.sudo_calls()))

    def test_fedora_rhel_and_opensuse_write_the_brave_repo(self):
        cases = (
            ({'ID': 'fedora', 'VERSION_ID': '41'},
             ['dnf', 'config-manager', 'addrepo', f'--from-repofile={RPM_URL}']),
            ({'ID': 'fedora', 'VERSION_ID': '40'},
             ['dnf', 'config-manager', '--add-repo', RPM_URL]),
            ({'ID': 'rhel', 'VERSION_ID': '"9.4"', 'ID_LIKE': 'fedora'},
             ['dnf', 'config-manager', '--add-repo', RPM_URL]),
            ({'ID': 'opensuse-tumbleweed', 'ID_LIKE': '"suse opensuse"'},
             ['zypper', '--non-interactive', '--gpg-auto-import-keys', 'addrepo', RPM_URL]),
        )
        for fields, expected in cases:
            with self.subTest(fields=fields):
                self.reset_install_state()
                self.write_os_release(**fields)
                self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
                binary = self.root / 'usr' / 'bin' / 'brave-browser'
                calls = self.sudo_calls()
                self.assertIn(expected, calls)
                self.assertTrue(binary.exists())
                if fields['ID'] == 'opensuse-tumbleweed':
                    self.assertIn(
                        ['zypper', '--non-interactive', '--gpg-auto-import-keys', 'install', 'brave-browser'],
                        calls)
                else:
                    plugin = ['dnf', 'install', '-y', 'dnf-plugins-core']
                    self.assertIn(plugin, calls)
                    self.assertLess(calls.index(plugin), calls.index(expected))

    def test_missing_rpm_repo_file_is_added_again_when_the_marker_remains(self):
        cases = (
            ({'ID': 'fedora', 'VERSION_ID': '41'},
             self.root / 'etc/yum.repos.d/brave-browser.repo',
             ['dnf', 'config-manager', 'addrepo', f'--from-repofile={RPM_URL}']),
            ({'ID': 'opensuse-tumbleweed', 'ID_LIKE': '"suse opensuse"'},
             self.root / 'etc/zypp/repos.d/brave-browser.repo',
             ['zypper', '--non-interactive', '--gpg-auto-import-keys', 'addrepo', RPM_URL]),
        )
        for fields, repo, expected in cases:
            with self.subTest(fields=fields, kind='absent'):
                self.reset_install_state()
                self.write_os_release(**fields)
                self.state_path('brave-rpm-repo-added').parent.mkdir(parents=True)
                self.state_path('brave-rpm-repo-added').write_text('old\n')
                self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
                self.assertIn(expected, self.sudo_calls())
                self.assertTrue(repo.is_file())
                self.assertGreater(repo.stat().st_size, 0)
                self.assertTrue((self.root / 'usr/bin/brave-browser').exists())
            with self.subTest(fields=fields, kind='empty'):
                self.reset_install_state()
                self.write_os_release(**fields)
                self.state_path('brave-rpm-repo-added').parent.mkdir(parents=True)
                self.state_path('brave-rpm-repo-added').write_text('old\n')
                repo.parent.mkdir(parents=True)
                repo.write_text('')
                self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
                calls = self.sudo_calls()
                self.assertIn(expected, calls)
                self.assertLess(calls.index(['rm', '-f', '--', str(repo)]), calls.index(expected))
                self.assertGreater(repo.stat().st_size, 0)
        self.reset_install_state()
        self.write_os_release(ID='fedora', VERSION_ID='41')
        repo = self.root / 'etc/yum.repos.d/brave-browser.repo'
        repo.parent.mkdir(parents=True)
        repo.write_text('repo\n')
        self.state_path('brave-rpm-repo-added').parent.mkdir(parents=True)
        self.state_path('brave-rpm-repo-added').write_text('old\n')
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        calls = self.sudo_calls()
        self.assertFalse(any('addrepo' in call or '--add-repo' in call for call in calls))
        self.assertTrue(any('dnf' in call and 'brave-browser' in call for call in calls))

    def test_arch_uses_an_aur_helper_or_prints_the_command(self):
        self.write_os_release(ID='arch')
        missing = self.run_script()
        self.assertIn('yay -Sy brave-bin', missing.stdout)
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        (self.bin / 'yay').symlink_to(self.bin / 'stub')
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
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
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
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

    def test_forced_extension_refuses_the_spec(self):
        spec = {
            'schemaVersion': 1,
            'default': {'id': 'brave', 'channel': 'release',
                        'desktopIds': {'linux': DESKTOP_ID}},
            'policies': [],
            'extensions': [{
                'name': 'Bitwarden',
                'id': BITWARDEN,
                'install': 'force',
                'updateUrl': 'https://clients2.google.com/service/update2/crx',
            }],
        }
        path = self.root / 'forced-spec.json'
        path.write_text(json.dumps(spec))
        self.env['GROUNDWORK_BRAVE_SPEC'] = str(path)
        result = self.run_script(status=1)
        self.assertIn('never forced', result.stderr)
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse(self.extension_path().exists())
        self.assertFalse(self.policy_path().exists())

    def xdg_sets(self):
        return [call[1:] for call in self.calls() if call[0] == 'xdg-settings' and call[1] == 'set']

    def launch_log(self):
        return (self.root / 'usr' / 'bin' / 'brave-launch.log').read_text()

    def test_stock_default_switches_once_after_the_launch_check(self):
        self.env['FIXTURE_DEFAULT_BROWSER'] = 'firefox.desktop'
        text = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.assertIn('a Brave window with a throwaway profile opens', text)
        self.assertIn('Brave is now the default browser', text)
        self.assertIn('xdg-settings set default-web-browser firefox.desktop', text)
        self.assertEqual(self.xdg_sets(), [['set', 'default-web-browser', DESKTOP_ID]])
        self.assertEqual((self.root / 'default-browser').read_text().strip(), DESKTOP_ID)
        self.assertTrue(self.state_path('brave-default-set').is_file())
        self.assertFalse(self.state_path('brave-default-declined').exists())

    def test_launch_uses_a_throwaway_profile_and_a_private_environment(self):
        self.env['SECRET_TOKEN'] = 'leak'
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        log = self.launch_log()
        self.assertIn('--user-data-dir=', log)
        self.assertNotIn(str(self.root / '.config'), log)
        self.assertIn('--no-first-run', log)
        self.assertNotIn('--headless', log)
        self.assertNotIn('SECRET_TOKEN', log)
        self.assertNotIn('WRAPPER_FIXTURE', log)
        self.assertNotIn(f'HOME={self.root}\n', log)
        data_dir = [line for line in log.splitlines() if '--user-data-dir=' in line][0].split('=', 1)[1]
        self.assertFalse(Path(data_dir).exists())

    def test_default_is_never_switched_a_second_time(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.root.joinpath('default-browser').write_text('firefox.desktop\n')
        self.reset_calls()
        (self.root / 'usr' / 'bin' / 'brave-launch.log').unlink()
        again = self.run_pty([])
        self.assertNotIn('[y/N]', again)
        self.assertNotIn('Checking that Brave starts', again)
        self.assertEqual(self.xdg_sets(), [])
        self.assertEqual(self.root.joinpath('default-browser').read_text().strip(), 'firefox.desktop')
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-launch.log').exists())

    def test_brave_already_the_default_is_recorded_without_a_launch(self):
        self.env['FIXTURE_DEFAULT_BROWSER'] = DESKTOP_ID
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.assertTrue(self.state_path('brave-default-set').is_file())
        self.assertEqual(self.xdg_sets(), [])
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-launch.log').exists())

    def test_other_default_gets_the_offer_and_a_no_is_saved(self):
        self.env['FIXTURE_DEFAULT_BROWSER'] = 'vivaldi-stable.desktop'
        declined = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'n')])
        self.assertIn('will not ask again', declined)
        self.assertTrue(self.state_path('brave-default-declined').is_file())
        self.assertFalse(self.state_path('brave-default-set').exists())
        self.assertEqual(self.xdg_sets(), [])
        self.reset_calls()
        again = self.run_pty([])
        self.assertNotIn('[y/N]', again)
        self.assertEqual(self.xdg_sets(), [])

    def test_other_default_offer_accepted_sets_and_records(self):
        self.env['FIXTURE_DEFAULT_BROWSER'] = 'vivaldi-stable.desktop'
        text = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'y')])
        self.assertIn('Brave is now the default browser', text)
        self.assertEqual(self.xdg_sets(), [['set', 'default-web-browser', DESKTOP_ID]])
        self.assertTrue(self.state_path('brave-default-set').is_file())

    def test_saved_decline_blocks_the_automatic_switch(self):
        self.state_path('brave-default-declined').parent.mkdir(parents=True)
        self.state_path('brave-default-declined').write_text('')
        self.env['FIXTURE_DEFAULT_BROWSER'] = 'firefox.desktop'
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.assertEqual(self.xdg_sets(), [])
        self.assertFalse(self.state_path('brave-default-set').exists())

    def test_failed_launch_checks_do_not_change_or_record_the_default(self):
        for mode, reason in (('crash', 'status 139'), ('hang', 'did not close'), ('badexit', 'status 3')):
            with self.subTest(mode=mode):
                self.reset_install_state()
                self.env['FIXTURE_BRAVE_MODE'] = mode
                self.env['FIXTURE_DEFAULT_BROWSER'] = 'firefox.desktop'
                text = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
                self.assertIn("launch check did not pass", text)
                self.assertIn(reason, text)
                self.assertEqual(self.xdg_sets(), [])
                self.assertFalse(self.state_path('brave-default-set').exists())
                self.assertFalse(self.state_path('brave-default-declined').exists())

    def test_default_not_confirmed_by_xdg_settings_get_is_not_recorded(self):
        self.env['FIXTURE_DEFAULT_BROWSER'] = 'firefox.desktop'
        self.env['FIXTURE_XDG_IGNORE_SET'] = '1'
        text = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.assertIn('The default browser was not changed', text)
        self.assertFalse(self.state_path('brave-default-set').exists())

    def test_no_desktop_session_defers_the_default_with_one_line(self):
        self.env['FIXTURE_DEFAULT_BROWSER'] = 'firefox.desktop'
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.reset_install_state()
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        self.env['FIXTURE_SUDO_NONINTERACTIVE'] = '1'
        self.run_script()
        self.reset_install_state()
        self.env.pop('GROUNDWORK_UPDATE_SCOPE')
        self.env.pop('FIXTURE_SUDO_NONINTERACTIVE')
        # headless = false in chezmoi config overrides the display check at the top.
        config = self.root / '.config' / 'chezmoi' / 'chezmoi.toml'
        config.parent.mkdir(parents=True)
        config.write_text('headless = false\n')
        self.env.pop('DISPLAY')
        text = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.assertEqual(text.count('no desktop session'), 1)
        self.assertEqual(self.xdg_sets(), [])
        self.assertFalse(self.state_path('brave-default-set').exists())

    def test_update_all_in_a_desktop_session_switches_a_stock_default_once(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.state_path('brave-default-set').unlink()
        self.root.joinpath('default-browser').write_text('firefox.desktop\n')
        self.reset_calls()
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        first = self.run_script()
        self.assertIn('Brave is now the default browser', first.stdout)
        self.assertEqual(self.xdg_sets(), [['set', 'default-web-browser', DESKTOP_ID]])
        self.root.joinpath('default-browser').write_text('firefox.desktop\n')
        self.reset_calls()
        second = self.run_script()
        self.assertNotIn('default browser', second.stdout)
        self.assertEqual(self.xdg_sets(), [])

    def test_no_terminal_apply_switches_stock_but_only_prints_for_other_defaults(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.state_path('brave-default-set').unlink()
        self.root.joinpath('default-browser').write_text('vivaldi-stable.desktop\n')
        self.reset_calls()
        other = self.run_script()
        self.assertEqual(self.xdg_sets(), [])
        self.assertEqual(other.stdout.count('Brave is not the default browser.'), 1)
        self.assertIn('xdg-settings set default-web-browser brave-browser.desktop', other.stdout)
        self.assertNotIn('Checking that Brave starts', other.stdout)
        self.root.joinpath('default-browser').write_text('firefox.desktop\n')
        stock = self.run_script()
        self.assertEqual(self.xdg_sets(), [['set', 'default-web-browser', DESKTOP_ID]])
        self.assertIn('Brave is now the default browser', stock.stdout)

    def test_configuration_apply_keeps_brave_and_still_makes_the_one_time_switch(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.state_path('brave-default-set').unlink()
        self.root.joinpath('default-browser').write_text('firefox.desktop\n')
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'configuration'
        result = self.run_script()
        self.assertIn('keeping the installed Brave', result.stdout)
        self.assertIn('Brave is now the default browser', result.stdout)

    def test_extension_offer_is_written_only_after_yes(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'y')])
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
        self.assertIn('separate profile', declined.lower())
        self.assertIn('stays installed', declined.lower())
        self.assertIn('brave://settings/importData', declined)
        self.assertIn('Passwords stay in Bitwarden', declined)
        self.assertTrue(self.state_path('brave-repo-move-declined').is_file())
        self.assertEqual((data / 'profile').read_text(), 'keep\n')
        self.assertFalse(any('uninstall' in call or 'remove' in call for call in self.calls()))
        self.assertNotIn('data directory', declined.lower())
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        self.reset_calls()
        reminder = self.run_pty([])
        self.assertIn('separate profile', reminder.lower())
        self.assertIn('stays installed', reminder.lower())
        self.assertIn('brave://settings/importData', reminder)
        self.assertIn('Passwords stay in Bitwarden', reminder)
        self.assertNotIn('data directory', reminder.lower())
        self.assertNotIn('[y/N]', reminder)
        self.assertFalse((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        self.state_path('brave-repo-move-declined').unlink()
        self.reset_calls()
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.assertTrue((self.root / 'usr' / 'bin' / 'brave-browser').exists())
        self.assertEqual((data / 'profile').read_text(), 'keep\n')
        self.assertFalse(any('uninstall' in call for call in self.calls()))

    def test_configuration_keeps_an_installed_brave_and_maintenance_does_not_install(self):
        self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n')])
        self.reset_calls()
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'configuration'
        kept = self.run_script()
        self.assertIn('keeping the installed Brave', kept.stdout)
        self.assertEqual([call for call in self.sudo_calls() if 'apt' in call], [])
        self.env['GROUNDWORK_UPDATE_SCOPE'] = 'maintenance'
        self.env['FIXTURE_SUDO_NONINTERACTIVE'] = '1'
        binary = self.root / 'usr' / 'bin' / 'brave-browser'
        self.policy_path().unlink()
        self.reset_calls()
        rewritten = self.run_script()
        self.assertTrue(self.policy_path().exists())
        self.assertTrue(binary.exists())
        self.assertEqual([call for call in self.sudo_calls() if 'apt' in call and 'install' in call], [])
        self.assertNotIn('[y/N]', rewritten.stdout + rewritten.stderr)
        binary.unlink()
        self.policy_path().unlink()
        self.reset_calls()
        deferred = self.run_script()
        self.assertIn('Brave is not installed.', deferred.stdout)
        self.assertNotIn('Installed Brave', deferred.stdout)
        self.assertFalse(binary.exists())
        self.assertFalse(self.policy_path().exists())
        self.assertEqual(self.sudo_calls(), [])
        self.assertFalse(any(call[0] == 'curl' for call in self.calls()))
        self.assertNotIn('[y/N]', deferred.stdout + deferred.stderr)

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
        self.reset_calls()
        self.env['FIXTURE_DEFAULT_BROWSER'] = 'vivaldi-stable.desktop'
        default_eof = self.run_pty([(b'[y/N]', 'y'), (b'[y/N]', 'n'), (b'[y/N]', 'EOF')])
        self.assertIn('was not changed', default_eof)
        self.assertFalse(self.state_path('brave-default-declined').exists())
        self.assertNotIn(
            ['set', 'default-web-browser', DESKTOP_ID],
            [call[1:] for call in self.calls() if call[0] == 'xdg-settings'])

    def test_sudo_password_prompt_is_announced_before_sudo_reads(self):
        self.env['FIXTURE_SUDO_PASSWORD'] = '1'
        text = self.run_pty([
            (b'[y/N]', 'y'),
            (b'Password:', 'secret'),
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
