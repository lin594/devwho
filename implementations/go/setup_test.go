//go:build setup

package main

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"reflect"
	"runtime"
	"strings"
	"testing"
)

var setupBinary string

func TestMain(m *testing.M) {
	dir, e := os.MkdirTemp("", "devwho-setup-tests-")
	if e != nil {
		panic(e)
	}
	setupBinary = filepath.Join(dir, "devwho-setup")
	cmd := exec.Command(runtime.GOROOT()+"/bin/go", "build", "-tags", "setup", "-o", setupBinary, ".")
	if out, e := cmd.CombinedOutput(); e != nil {
		os.Stderr.Write(out)
		os.RemoveAll(dir)
		panic(e)
	}
	code := m.Run()
	os.RemoveAll(dir)
	os.Exit(code)
}

const setupFixture = `version = 1
# exact original comment
[settings]
default_profile = "a"
shortcut_profile = "a"
handoff_warning = true
[profiles.a]
unset_env = ["DELETE"]
[profiles.a.git]
name = "Original User"
email = "original@example.test"
signing_format = "ssh"
sign_commits = false
[profiles.a.git.config]
"credential.helper" = ["", "private-helper"]
"core.editor" = "second"
"http.proxy" = "private-proxy"
[profiles.a.git_ssh]
identity_file = "/tmp/nonexistent-editor-key"
identities_only = false
[profiles.a.github]
config_dir = "/tmp/gh"
expected_user = "a_work"
hostname = "example.test"
[profiles.a.env]
SECRET = "fictional-secret"
MULTI = "line\nquote' \" 雪\u0001"
[profiles.b.env]
OTHER = "retain"
`

func setupDoc(t *testing.T) *Document {
	t.Helper()
	d, e := parseDocumentTOML([]byte(setupFixture))
	if e != nil {
		t.Fatal(e)
	}
	return d
}
func TestSetupSchemaJSONStrictnessAndOrderedRoundtrip(t *testing.T) {
	doc := setupDoc(t)
	raw := []byte(orderedJSON(doc.Data, nil, doc.Orders))
	next, e := parseDocumentJSON(raw)
	if e != nil {
		t.Fatal(e)
	}
	toml, e := renderDocumentTOML(next)
	if e != nil {
		t.Fatal(e)
	}
	roundtrip, e := parseDocumentTOML(toml)
	if e != nil {
		t.Fatal(e)
	}
	if !reflect.DeepEqual(doc.Data, roundtrip.Data) || !reflect.DeepEqual(doc.Orders, roundtrip.Orders) {
		t.Fatal("JSON/TOML roundtrip altered fields or Git ordering")
	}
	for _, raw := range []string{`{"version":1,"version":1,"profiles":{"a":{}}}`, `{"version":1,"profiles":{"a":{"env":{"X":"one","X":"two"}}}}`, `{"version":1.0,"profiles":{"a":{}}}`, `{"version":1e0,"profiles":{"a":{}}}`, `{"version":true,"profiles":{"a":{}}}`, `{"version":1,"profiles":{"a":{}},"unknown":true}`, `{"version":1,"profiles":{"a":{"env":{"X":"\ud800"}}}}`, `{"version":1,"profiles":{"a":{}}} {}`, `{"revision":"missing","configuration":{"version":1,"profiles":{"a":{}}},"redacted":true}`, strings.Repeat(" ", 1024*1024+1)} {
		if _, e := parseDocumentJSON([]byte(raw)); e == nil {
			t.Fatalf("invalid setup JSON accepted: %.100s", raw)
		}
	}
}
func TestSetupReadRedactionAndOptIn(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.toml")
	os.WriteFile(path, []byte(setupFixture), 0600)
	for _, show := range []bool{false, true} {
		args := []string{"--config", path, "read"}
		if show {
			args = append(args, "--show-values")
		}
		var out, err bytes.Buffer
		code, e := setupArgs(args, strings.NewReader(""), &out, &err)
		if e != nil || code != 0 {
			t.Fatalf("read: %d %v %s", code, e, err.String())
		}
		s := out.String()
		for _, value := range []string{"fictional-secret", "private-helper", "private-proxy"} {
			if strings.Contains(s, value) != show {
				t.Fatal("redaction opt-in mismatch")
			}
		}
		var envelope map[string]any
		if e := json.Unmarshal(out.Bytes(), &envelope); e != nil {
			t.Fatal(e)
		}
		if envelope["revision"] != revision([]byte(setupFixture)) || envelope["redacted"] == show {
			t.Fatal("read envelope")
		}
		if _, e := parseDocumentJSON(out.Bytes()); e == nil {
			t.Fatal("read envelope silently accepted as replacement")
		}
	}
	if !strings.Contains(orderedJSON(setupDoc(t).Data, nil, setupDoc(t).Orders), "private-helper") {
		t.Fatal("redaction mutated source")
	}
}
func TestSetupAtomicSaveAndBackupModes(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "config.toml")
	os.WriteFile(path, []byte(setupFixture), 0644)
	doc := setupDoc(t)
	p := doc.Data["profiles"].(map[string]any)["a"].(map[string]any)
	p["git"].(map[string]any)["name"] = "Updated User"
	saved, e := storeSave(path, doc, revision([]byte(setupFixture)))
	if e != nil {
		t.Fatal(e)
	}
	if saved.Revision == revision([]byte(setupFixture)) {
		t.Fatal("revision did not advance")
	}
	stat, _ := os.Stat(path)
	if stat.Mode().Perm() != 0600 {
		t.Fatal("replacement mode")
	}
	backups := filepath.Join(dir, ".devwho-backups")
	stat, _ = os.Stat(backups)
	if stat.Mode().Perm() != 0700 {
		t.Fatal("backup dir mode")
	}
	entries, e := os.ReadDir(backups)
	if e != nil || len(entries) != 1 {
		t.Fatal("backup count")
	}
	bp := filepath.Join(backups, entries[0].Name())
	raw, _ := os.ReadFile(bp)
	if string(raw) != setupFixture {
		t.Fatal("backup altered original bytes")
	}
	stat, _ = os.Stat(bp)
	if stat.Mode().Perm() != 0600 {
		t.Fatal("backup mode")
	}
	original, _ := os.ReadFile(path)
	if _, e := storeSave(path, doc, revision([]byte(setupFixture))); e == nil {
		t.Fatal("stale save accepted")
	}
	after, _ := os.ReadFile(path)
	entries, _ = os.ReadDir(backups)
	if !bytes.Equal(original, after) || len(entries) != 1 {
		t.Fatal("stale save caused writes")
	}
	if _, e := storeSave(path, doc, "missing"); e == nil {
		t.Fatal("missing CAS overwrote existing file")
	}
}
func TestSetupRejectsSymlinksAndUnsafeBackup(t *testing.T) {
	for _, kind := range []string{"config", "lock", "backup"} {
		t.Run(kind, func(t *testing.T) {
			dir := t.TempDir()
			path := filepath.Join(dir, "config.toml")
			target := filepath.Join(dir, "target")
			os.WriteFile(target, []byte(setupFixture), 0600)
			expected := "missing"
			switch kind {
			case "config":
				os.Symlink(target, path)
				expected = revision([]byte(setupFixture))
			case "lock":
				os.Symlink(target, path+".lock")
			case "backup":
				os.WriteFile(path, []byte(setupFixture), 0600)
				os.Symlink(dir, filepath.Join(dir, ".devwho-backups"))
				expected = revision([]byte(setupFixture))
			}
			if _, e := storeSave(path, setupDoc(t), expected); e == nil {
				t.Fatal("unsafe path accepted")
			}
			raw, _ := os.ReadFile(target)
			if string(raw) != setupFixture {
				t.Fatal("symlink target changed")
			}
		})
	}
}
func TestSetupCrossProcessCAS(t *testing.T) {
	path := filepath.Join(t.TempDir(), "config.toml")
	os.WriteFile(path, []byte(setupFixture), 0600)
	original := revision([]byte(setupFixture))
	cmds := []*exec.Cmd{}
	outs := []*bytes.Buffer{}
	for _, name := range []string{"Writer One", "Writer Two"} {
		doc := setupDoc(t)
		doc.Data["profiles"].(map[string]any)["a"].(map[string]any)["git"].(map[string]any)["name"] = name
		cmd := exec.Command(setupBinary, "--config", path, "replace", "--if-revision", original)
		cmd.Stdin = strings.NewReader(orderedJSON(doc.Data, nil, doc.Orders))
		out := &bytes.Buffer{}
		cmd.Stdout = out
		cmd.Stderr = out
		if e := cmd.Start(); e != nil {
			t.Fatal(e)
		}
		cmds = append(cmds, cmd)
		outs = append(outs, out)
	}
	success, stale := 0, 0
	for i, cmd := range cmds {
		if e := cmd.Wait(); e == nil {
			success++
		} else if strings.Contains(outs[i].String(), "revision changed") {
			stale++
		} else {
			t.Fatalf("unexpected writer failure %v %s", e, outs[i])
		}
	}
	if success != 1 || stale != 1 {
		t.Fatalf("CAS writers success=%d stale=%d", success, stale)
	}
	entries, _ := os.ReadDir(filepath.Join(filepath.Dir(path), ".devwho-backups"))
	if len(entries) != 1 {
		t.Fatal("losing writer made backup")
	}
	if _, e := storeRead(path); e != nil {
		t.Fatal(e)
	}
}
func TestSetupConfigureCancelAndRetainsAdvancedFields(t *testing.T) {
	for _, language := range []string{"en", "zh-CN"} {
		for _, save := range []bool{false, true} {
			t.Run(language+map[bool]string{true: "save", false: "cancel"}[save], func(t *testing.T) {
				path := filepath.Join(t.TempDir(), "config.toml")
				os.WriteFile(path, []byte(setupFixture), 0600)
				answers := []string{"a", "Edited User", "", "", "", "", "", "", "", "cancel"}
				if save {
					answers[len(answers)-1] = "save"
				}
				var out, err bytes.Buffer
				code, e := setupArgs([]string{"--config", path, "--language", language, "configure"}, strings.NewReader(strings.Join(answers, "\n")+"\n"), &out, &err)
				if e != nil || code != 0 {
					t.Fatalf("configure %v %d %s", e, code, out.String())
				}
				if strings.Contains(out.String(), "fictional-secret") || strings.Contains(out.String(), "private-helper") {
					t.Fatal("UI preview leaked values")
				}
				raw, _ := os.ReadFile(path)
				if !save {
					if string(raw) != setupFixture {
						t.Fatal("cancel changed configuration")
					}
					if _, e := os.Stat(path + ".lock"); !os.IsNotExist(e) {
						t.Fatal("cancel acquired write lock")
					}
					return
				}
				doc, e := parseDocumentTOML(raw)
				if e != nil {
					t.Fatal(e)
				}
				expected := setupDoc(t)
				expected.Data["profiles"].(map[string]any)["a"].(map[string]any)["git"].(map[string]any)["name"] = "Edited User"
				if !reflect.DeepEqual(doc.Data, expected.Data) || !reflect.DeepEqual(doc.Orders, expected.Orders) {
					t.Fatal("UI lost advanced/unrelated fields")
				}
			})
		}
	}
}
func TestSetupMissingReadAndCreation(t *testing.T) {
	path := filepath.Join(t.TempDir(), "new", "config.toml")
	var out, err bytes.Buffer
	code, e := setupArgs([]string{"--config", path, "read"}, strings.NewReader(""), &out, &err)
	if e != nil || code != 0 || !strings.Contains(out.String(), `"revision":"missing"`) || !strings.Contains(out.String(), `"configuration":null`) {
		t.Fatal("missing read envelope")
	}
	doc, e := parseDocumentJSON([]byte(`{"version":1,"profiles":{"new":{"env":{"VALUE":"literal"}}}}`))
	if e != nil {
		t.Fatal(e)
	}
	if _, e = storeSave(path, doc, "missing"); e != nil {
		t.Fatal(e)
	}
	if _, e = os.Stat(filepath.Join(filepath.Dir(path), ".devwho-backups")); !os.IsNotExist(e) {
		t.Fatal("new file had a fake baseline backup")
	}
}
