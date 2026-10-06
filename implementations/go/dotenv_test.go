package main

import (
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

func TestDotenvLiteralGrammar(t *testing.T) {
	data := "# header\r\nexport DEVWHO_PROFILE = 'work' # selection\r\nEMPTY=\r\n SPACED =  text with spaces \t # comment\r\nHASH=#literal\r\nREF= $HOME ${HOME} $(false) `false`\r\nSINGLE='a\\b $HOME #tag'\r\nDOUBLE=\"line\\n雪\\t\\uD83D\\uDE03\"# comment\r\n"
	p, e := parseDotenv([]byte(data), "")
	if e != nil {
		t.Fatal(e)
	}
	want := Env{"EMPTY": "", "SPACED": "text with spaces", "HASH": "#literal", "REF": "$HOME ${HOME} $(false) `false`", "SINGLE": `a\b $HOME #tag`, "DOUBLE": "line\n雪\t😃"}
	if p.Name != "work" || !reflect.DeepEqual(p.Env, want) {
		t.Fatalf("literal grammar: %#v", p)
	}
	if _, e := parseDotenv([]byte("EMPTY=\n"), "explicit"); e != nil {
		t.Fatal(e)
	}
	for _, data := range []string{"DEVWHO_PROFILE=\n", "DEVWHO_PROFILE=work\nDEVWHO_PROFILE=work", "DEVWHO_PROFILE=work\nX=a\nX=b", "DEVWHO_PROFILE=work\nBARE", "DEVWHO_PROFILE=work\nX='bad", "DEVWHO_PROFILE=work\nX=\"bad\\q\"", "DEVWHO_PROFILE=work\nX=\"\\uD800\"", "DEVWHO_PROFILE=work\nX=\"\\uDC00\"", "DEVWHO_PROFILE=work\nX=\"\\uD800\\u0030\"", "DEVWHO_PROFILE=work\nX=\"valid\" suffix", "DEVWHO_PROFILE=work\nX=\"\\u0000\"", "DEVWHO_PROFILE=work\nX=raw\rvalue", "DEVWHO_PROFILE=work\nX=\x00", "DEVWHO_PROFILE=work\nX=\xff", "DEVWHO_PROFILE=work\nGIT_AUTHOR_NAME=bad", "DEVWHO_PROFILE=work\nGIT_CONFIG_COUNT=1", "DEVWHO_PROFILE=work\nBASH_ENV=bad"} {
		if _, e := parseDotenv([]byte(data), ""); e == nil {
			t.Fatalf("invalid dotenv accepted: %q", data)
		}
	}
	if _, e := parseDotenv([]byte("DEVWHO_PROFILE=work"), "other"); e == nil {
		t.Fatal("profile mismatch accepted")
	}
}
func TestDotenvExportRoundtripAndLossRejection(t *testing.T) {
	values := map[string]any{"EMPTY": "", "VALUE": "quote' \" $HOME \n 雪 \x01", "GH_TOKEN": "fictional-secret"}
	p, e := parseProfile("work", map[string]any{"env": values}, nil)
	if e != nil {
		t.Fatal(e)
	}
	text, e := exportDotenv(p)
	if e != nil {
		t.Fatal(e)
	}
	next, e := parseDotenv([]byte(text), "")
	if e != nil {
		t.Fatal(e)
	}
	if !reflect.DeepEqual(p.Env, next.Env) {
		t.Fatal("export altered literal data")
	}
	for _, raw := range []map[string]any{{"git": map[string]any{"sign_commits": false}}, {"git_ssh": map[string]any{"identity_file": "/tmp/key"}}, {"github": map[string]any{"config_dir": "/tmp/gh", "expected_user": "work"}}, {"unset_env": []any{"VALUE"}}} {
		p, e := parseProfile("a", raw, nil)
		if e != nil {
			t.Fatal(e)
		}
		if _, e := exportDotenv(p); e == nil {
			t.Fatal("lossy export accepted")
		}
	}
}
func TestDotenvShellPinAndNoDefault(t *testing.T) {
	path := filepath.Join(t.TempDir(), "profile.env")
	if e := os.WriteFile(path, []byte("DEVWHO_PROFILE=work\nVALUE='literal $HOME'\n"), 0600); e != nil {
		t.Fatal(e)
	}
	cfg, e := loadDotenv(path, "", Env{})
	if e != nil {
		t.Fatal(e)
	}
	if cfg.Default != "" || cfg.Shortcut != "work" || !cfg.EnvFile {
		t.Fatal("dotenv lifecycle metadata")
	}
	for _, shell := range []string{"bash", "zsh"} {
		text, e := renderInit(shell, cfg)
		if e != nil {
			t.Fatal(e)
		}
		if !strings.Contains(text, "--env-file "+quote(path)+" --env-profile work") || strings.Contains(text, "__devwho_bootstrap") {
			t.Fatal("init source pin/default")
		}
	}
	// Drive a fresh build of the actual CLI through both shell adapters.
	exe := filepath.Join(t.TempDir(), "devwho")
	cmd := exec.Command(runtime.GOROOT()+"/bin/go", "build", "-o", exe, ".")
	if out, e := cmd.CombinedOutput(); e != nil {
		t.Fatalf("build: %v %s", e, out)
	}
	for _, shell := range []string{"bash", "zsh"} {
		s, e := exec.LookPath(shell)
		if e != nil {
			continue
		}
		script := "set -e\neval \"$(" + quote(exe) + " --env-file " + quote(path) + " init " + shell + ")\"\n[ \"${DEVWHO_PROFILE-missing}\" = missing ]\nsetdev\n[ \"$VALUE\" = 'literal $HOME' ]\ncd /\nunsetdev\n[ \"${VALUE-missing}\" = missing ]\n"
		args := []string{"--noprofile", "--norc", "-c", script}
		if shell == "zsh" {
			args = []string{"-f", "-c", script}
		}
		cmd := exec.Command(s, args...)
		env := environment()
		delete(env, "DEVWHO_PROFILE")
		delete(env, "VALUE")
		cmd.Env = envList(env)
		if out, e := cmd.CombinedOutput(); e != nil {
			t.Fatalf("%s lifecycle: %v %s", shell, e, out)
		}
	}
}
