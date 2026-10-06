"""Optional dotenv frontend: dev-only Python tests of the executable contract."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

EXE=Path(__file__).resolve().parents[1]/'devwho'

class DotenvTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.path=Path(self.tmp.name)/'profile.env'
    def tearDown(self):self.tmp.cleanup()
    def run_cli(self,*args):
        return subprocess.run([str(EXE),'--env-file',str(self.path),*args],text=True,capture_output=True)
    def test_literal_grammar(self):
        self.path.write_bytes(b'DEVWHO_PROFILE=demo\r\nexport A = "hi\\n\\u4e2d" # comment\r\nB=literal ${HOME} $(false) # hidden\r\nC=abc#literal\r\nD=\r\nE=\'literal \\n\'\r\n')
        p=self.run_cli('exec','demo','--','jq','-n','env');self.assertEqual(p.returncode,0,p.stderr)
        env=json.loads(p.stdout)
        self.assertEqual({k:env[k] for k in ('A','B','C','D','E')},{'A':'hi\n中','B':'literal ${HOME} $(false)','C':'abc#literal','D':'','E':'literal \\n'})
    def test_explicit_profile_and_export_roundtrip(self):
        self.path.write_text('A="one\\ntwo"\nEMPTY=\n')
        p=self.run_cli('--env-profile','demo','config','export-env','demo');self.assertEqual(p.returncode,0,p.stderr)
        self.path.write_text(p.stdout)
        self.assertEqual(self.run_cli('list').stdout,'demo\n')
        p=self.run_cli('exec','demo','--','jq','-n','env');self.assertEqual(json.loads(p.stdout)['A'],'one\ntwo')
    def test_rejections(self):
        cases=['A=x', 'DEVWHO_PROFILE=\n', 'DEVWHO_PROFILE=a\nA=x\nA=y', 'DEVWHO_PROFILE=a\nBASH_ENV=x', 'DEVWHO_PROFILE=a\nA="\\uD800"', 'DEVWHO_PROFILE=a\nA="\\u0000"', 'DEVWHO_PROFILE=a\nA="x" junk', 'DEVWHO_PROFILE=a\nA="physical\nnewline"', 'DEVWHO_PROFILE=a\nA=x\rB=y', 'DEVWHO_PROFILE=a\nBAREKEY']
        for value in cases:
            with self.subTest(value=value):
                self.path.write_text(value);p=self.run_cli('list');self.assertNotEqual(p.returncode,0);self.assertEqual(p.stdout,'')
        self.path.write_bytes(b'DEVWHO_PROFILE=a\nA=\xff');self.assertNotEqual(self.run_cli('list').returncode,0)
    def test_profile_mismatch(self):
        self.path.write_text('DEVWHO_PROFILE=a\nA=x')
        self.assertNotEqual(self.run_cli('--env-profile','b','list').returncode,0)
        self.assertNotEqual(self.run_cli('--config',str(self.path),'list').returncode,0)
        self.assertNotEqual(self.run_cli('config','init').returncode,0)
    def test_pinned_init_and_shortcut(self):
        self.path.write_text('DEVWHO_PROFILE=a\nA=x\nPATH=/missing')
        p=subprocess.run(['/bin/bash','-c','set -e; eval "$("$1" --env-file "$2" init bash)"; cd /; setdev; test "$A" = x; unsetdev; test -z "${A+x}"','test',str(EXE),str(self.path)],text=True,capture_output=True)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_semantics_export_rejected(self):
        self.path.write_text('version=1\n[profiles.a.git]\nname="A"\nemail="a@example.test"')
        p=subprocess.run([str(EXE),'--config',str(self.path),'config','export-env','a'],text=True,capture_output=True)
        self.assertNotEqual(p.returncode,0);self.assertEqual(p.stdout,'')

if __name__=='__main__':unittest.main()
