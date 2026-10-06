package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

type selectionCase struct {
	Name       string `json:"name"`
	EnvPresent bool   `json:"env_present"`
	Env        string `json:"env"`
	Explicit   string `json:"explicit"`
	Want       string `json:"want"`
	Error      string `json:"error"`
}

func TestSharedSelectionFixtures(t *testing.T) {
	b, err := os.ReadFile("../../conformance/native/selection.json")
	if err != nil {
		t.Fatal(err)
	}
	var fixture struct {
		Cases []selectionCase `json:"cases"`
	}
	if err := json.Unmarshal(b, &fixture); err != nil {
		t.Fatal(err)
	}
	c := config{DefaultAccount: "personal", Accounts: map[string]string{"personal": "p.txt", "work-account": "w.txt"}, Profiles: map[string]string{"work": "work-account"}}
	for _, tc := range fixture.Cases {
		t.Run(tc.Name, func(t *testing.T) {
			got, err := selectAccount(c, tc.Explicit, tc.Env, tc.EnvPresent)
			if tc.Error != "" {
				if err == nil || !strings.Contains(err.Error(), tc.Error) {
					t.Fatalf("error=%v, want containing %q", err, tc.Error)
				}
				return
			}
			if err != nil || got != tc.Want {
				t.Fatalf("got (%q, %v), want %q", got, err, tc.Want)
			}
		})
	}
}

func TestAddListUsesSelectedNotebookAndLiteralText(t *testing.T) {
	dir := t.TempDir()
	cfg := filepath.Join(dir, "app.json")
	contents := `{"default_account":"personal","accounts":{"personal":"personal.txt","work":"work.txt"},"profiles":{"work":"work"}}`
	if err := os.WriteFile(cfg, []byte(contents), 0600); err != nil {
		t.Fatal(err)
	}
	args := []string{"--config", cfg, "add", "$(touch nope); $HOME"}
	if code := run(args, func(string) (string, bool) { return "work", true }, &strings.Builder{}, &strings.Builder{}); code != 0 {
		t.Fatalf("add exit %d", code)
	}
	got, err := os.ReadFile(filepath.Join(dir, "work.txt"))
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != "$(touch nope); $HOME\n" {
		t.Fatalf("text changed: %q", got)
	}
	if _, err := os.Stat(filepath.Join(dir, "personal.txt")); !os.IsNotExist(err) {
		t.Fatalf("unexpected default notebook: %v", err)
	}
}

func TestInvalidSelectionFailsBeforeAnyNotebookWrite(t *testing.T) {
	dir := t.TempDir()
	cfg := filepath.Join(dir, "app.json")
	if err := os.WriteFile(cfg, []byte(`{"default_account":"personal","accounts":{"personal":"p.txt"},"profiles":{"work":"personal"}}`), 0600); err != nil {
		t.Fatal(err)
	}
	var stderr strings.Builder
	code := run([]string{"--config", cfg, "add", "do not write"}, func(string) (string, bool) { return "unmapped", true }, &strings.Builder{}, &stderr)
	if code == 0 {
		t.Fatal("expected error")
	}
	if _, err := os.Stat(filepath.Join(dir, "p.txt")); !os.IsNotExist(err) {
		t.Fatalf("notebook created before selection error: %v", err)
	}
}

func TestMalformedConfigFailsBeforeWrite(t *testing.T) {
	dir := t.TempDir()
	cfg := filepath.Join(dir, "app.json")
	if err := os.WriteFile(cfg, []byte(`{"default_account":"missing","accounts":{"personal":"p.txt"},"profiles":{}}`), 0600); err != nil {
		t.Fatal(err)
	}
	code := run([]string{"--config", cfg, "add", "text"}, func(string) (string, bool) { return "", false }, &strings.Builder{}, &strings.Builder{})
	if code == 0 {
		t.Fatal("expected malformed mapping error")
	}
	if _, err := os.Stat(filepath.Join(dir, "p.txt")); !os.IsNotExist(err) {
		t.Fatalf("notebook created for malformed config: %v", err)
	}
}
