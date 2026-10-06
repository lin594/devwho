"""Development-only tests. Runtime uses Bash, jq and Perl, never Python."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
EXE = ROOT / 'implementations/bash/devwho'

class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'config.toml'
        self.env = {k:v for k,v in os.environ.items() if not k.startswith(('DEVWHO_', 'GIT_CONFIG_', 'GIT_AUTHOR_', 'GIT_COMMITTER_'))}
        self.env.pop('GH_TOKEN', None)
        self.env.pop('GITHUB_TOKEN', None)
    def tearDown(self): self.tmp.cleanup()
    def config(self, value): self.path.write_text(value)
    def run_cli(self, *args, input='', env=None):
        return subprocess.run([str(EXE), '--config', str(self.path), *args], input=input, text=True, capture_output=True, env=env or self.env)
    def shell(self, text, shell='bash'):
        result=subprocess.run([shell, '-c', 'set -e\neval "$("$1" --config "$2" init '+shell+')"\n'+text, 'test', str(EXE), str(self.path)],capture_output=True,text=True,env=self.env)
        self.assertEqual(result.returncode,0,result.stderr+result.stdout)
        return result.stdout
    def test_literals_switch_restore(self):
        self.config('''version=1
[profiles.a.env]
TEXT="""a\n'$(touch /tmp/devwho-no-create)`false`\n"""
EMPTY=""
[profiles.b]
unset_env=["TEXT"]
[profiles.b.env]
B="b"
''')
        self.env["EXPECTED"] = "a\n'$(touch /tmp/devwho-no-create)`false`\n"
        self.shell('''export TEXT=original EMPTY=''
setdev a
test "$DEVWHO_PROFILE" = a
test "$TEXT" = "$EXPECTED"
setdev b
test -z "${TEXT+x}"
unsetdev
test "$TEXT" = original
test "${EMPTY+x}" = x
test -z "$EMPTY"
test -z "${B+x}"
test -z "${DEVWHO_PROFILE+x}"
''')
    def test_runtime_order_appendage_orphan(self):
        self.config('''version=1
[profiles.a.git.config]
"z.a"=["1","2"]
"a.z"="3"
[profiles.b.env]
B="b"
''')
        self.shell('''export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=base.key GIT_CONFIG_VALUE_0=base
export GIT_CONFIG_KEY_1=orphan GIT_CONFIG_VALUE_1=orphanvalue
setdev a
test "$GIT_CONFIG_KEY_1" = z.a
test "$GIT_CONFIG_VALUE_2" = 2
test "$GIT_CONFIG_KEY_3" = a.z
export GIT_CONFIG_COUNT=5 GIT_CONFIG_KEY_4=third.party GIT_CONFIG_VALUE_4=append
setdev b
test "$GIT_CONFIG_COUNT" = 2
test "$GIT_CONFIG_KEY_1" = third.party
unsetdev
test "$GIT_CONFIG_COUNT" = 2
test "$GIT_CONFIG_VALUE_1" = append
''')
    def test_readonly_atomic(self):
        self.config('version=1\n[profiles.a.env]\nFOO="changed"\nBAR="other"\n')
        self.shell('readonly FOO=old\nif setdev a; then exit 9; fi\ntest "$FOO" = old\ntest -z "${BAR+x}"\ntest -z "${DEVWHO_PROFILE+x}"')
    def test_zsh(self):
        self.config('version=1\n[profiles.a.env]\nFOO="changed"\n')
        self.shell('export FOO=old; setdev a; test "$FOO" = changed; unsetdev; test "$FOO" = old', 'zsh')
    def test_default_baseline(self):
        self.config('version=1\n[settings]\ndefault_profile="a"\nshortcut_profile="b"\n[profiles.a.env]\nFOO="a"\n[profiles.b.env]\nFOO="b"\n')
        self.shell('test "$FOO" = a; test -z "$__DEVWHO_STATE"; setdev; test "$FOO" = b; unsetdev; test "$FOO" = a')
    def test_valid_toml(self):
        cases=[
            'version=0x1\nprofiles.a.env={ FOO="hi", BAR="" }',
            "version=1\n[profiles.'a'.env]\nFOO='''a\\\nb'''\nBAR='''\nhi\n'''",
            'version=1\nprofiles.a.git.config={"a.b"=["one",\n"two",]}',
            'version=1\nprofiles.a.env.FOO="\\u4e2d\\U0001F600"',
            'version=1\nprofiles.a.env.FOO="\\r\\n"',
            'version=1\nprofiles.a.env.FOO="\\U0010FFFF"',
            'version=1\nprofiles.a.env.FOO="""two \\\\nnext"""',
            'version=1\n[profiles.a.env]\nFOO="""line \\\n  continued"""',
        ]
        import tomllib
        for value in cases:
            with self.subTest(value=value):
                self.config(value)
                result=self.run_cli('exec','a','--','jq','-n','env')
                self.assertEqual(result.returncode,0,result.stderr)
                expected=tomllib.loads(value)['profiles']['a'].get('env',{})
                for k,v in expected.items():self.assertEqual(json.loads(result.stdout)[k],v)
    def test_invalid_toml_schema(self):
        cases=[
            'version=1\nversion=1\n[profiles.a]',
            'version=1.0\n[profiles.a]',
            'version=true\n[profiles.a]',
            'version=1\n[profiles.a]\ngit=false',
            'version=1\n[profiles.a]\nunset_env=false',
            'version=1\n[profiles.a.env]\nBASH_ENV="bad"',
            'version=1\nprofiles={a={env={A="x"}}}\nprofiles.b={}',
            'version=1\nprofiles.a.env.A="x"\n[profiles.a.env]\nB="b"',
            'version=1\n[profiles.a.env]\nA="\\uD800"',
            'version=1\n[profiles.a.env]\nA="\\u12_3"',
            'version=1\n[profiles.a.env]\nA="x"\nA="y"',
            'version=1\nprofiles.a={env={A="x"},env.B="y"}',
            'version=1\n[profiles.a.env]\n"A\\n"="x"',
        ]
        for value in cases:
            with self.subTest(value=value):
                self.config(value);self.assertNotEqual(self.run_cli('list').returncode,0)
    def test_malformed_unowned_runtime_preserved(self):
        self.config('version=1\n[profiles.a.env]\nA="a"')
        self.env['GIT_CONFIG_COUNT']='invalid'
        self.shell('setdev a; test "$GIT_CONFIG_COUNT" = invalid; unsetdev; test "$GIT_CONFIG_COUNT" = invalid')
    def test_git_and_doctor(self):
        self.config('version=1\n[profiles.a.git]\nname="A Person"\nemail="a@test.example"')
        self.shell('setdev a; "$1" --config "$2" doctor --offline; test -z "${GIT_AUTHOR_NAME+x}"; git var GIT_AUTHOR_IDENT; unsetdev')
    def test_exec_status_and_missing(self):
        self.config('version=1\n[profiles.a]')
        self.assertEqual(self.run_cli('exec','a','--','/bin/sh','-c','exit 43').returncode,43)
        self.assertEqual(self.run_cli('exec','a','--','not-a-real-command').returncode,127)
        self.assertEqual(self.run_cli('exec','a','--',str(self.path)).returncode,126)
    def test_path_change_does_not_lose_transition_tools(self):
        self.config('version=1\n[profiles.a.env]\nPATH="/missing"\n[profiles.b]\nunset_env=["PATH"]')
        self.shell('old=$PATH; setdev a; test "$PATH" = /missing; setdev b; test -z "${PATH+x}"; unsetdev; test "$PATH" = "$old"')
    def test_exec_preserves_shell_special_environment(self):
        self.config('version=1\n[profiles.a]')
        self.env.update({'SHLVL':'77','PWD':'/literal-baseline','ODD-NAME':'literal','UNICODE_BASELINE':'中文😀\n'})
        result=self.run_cli('exec','a','--','/usr/bin/env')
        self.assertEqual(result.returncode,0,result.stderr)
        for key in ('SHLVL','PWD','ODD-NAME','UNICODE_BASELINE'):
            self.assertIn(key+'='+self.env[key]+'\n',result.stdout)
        self.config('version=1\n[profiles.a.env]\nSHLVL="not-a-number"\nPWD="/literal-target"')
        result=self.run_cli('exec','a','--','/usr/bin/env')
        self.assertIn('SHLVL=not-a-number\n',result.stdout)
        self.assertIn('PWD=/literal-target\n',result.stdout)
    def test_shell_special_baseline(self):
        self.config('version=1\n[profiles.a.env]\nSHLVL="77"\nPWD="/literal-target"\nTMPDIR="/missing-target-directory"')
        self.shell('before_level=$SHLVL; before_pwd=$PWD; setdev a; test "$SHLVL" = 77; test "$PWD" = /literal-target; unsetdev; test "$SHLVL" = "$before_level"; test "$PWD" = "$before_pwd"')
    def test_invalid_state(self):
        self.config('version=1\n[profiles.a]')
        for value in ['{', '{}', '{"version":true}', '[]', '{"version":1,"profile":"a","baseline":{},"managed":["X"],"runtime":null}']:
            with self.subTest(value=value): self.assertNotEqual(self.run_cli('internal','transition','--shell','bash','--activate','a',input=value).returncode,0)

if __name__=='__main__':unittest.main()
