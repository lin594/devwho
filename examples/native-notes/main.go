package main

import (
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

var labelPattern = regexp.MustCompile(`^[A-Za-z0-9][A-Za-z0-9_.-]*$`)

type config struct {
	DefaultAccount string            `json:"default_account"`
	Accounts       map[string]string `json:"accounts"`
	Profiles       map[string]string `json:"profiles"`
}

func readConfig(path string) (config, error) {
	var c config
	f, err := os.Open(path)
	if err != nil {
		return c, fmt.Errorf("open config: %w", err)
	}
	defer f.Close()
	dec := json.NewDecoder(f)
	dec.DisallowUnknownFields()
	if err := dec.Decode(&c); err != nil {
		return c, fmt.Errorf("decode config: %w", err)
	}
	if err := dec.Decode(new(any)); err != io.EOF {
		return c, errors.New("config must contain exactly one JSON value")
	}
	if c.DefaultAccount == "" || c.Accounts == nil || c.Profiles == nil {
		return c, errors.New("config requires default_account, accounts, and profiles")
	}
	if _, ok := c.Accounts[c.DefaultAccount]; !ok {
		return c, errors.New("default_account must name a configured account")
	}
	for id, path := range c.Accounts {
		if id == "" || strings.TrimSpace(path) == "" {
			return c, errors.New("account ids and storage paths must be nonempty")
		}
		if strings.IndexByte(path, 0) >= 0 {
			return c, errors.New("storage path contains NUL")
		}
	}
	for label, id := range c.Profiles {
		if !labelPattern.MatchString(label) {
			return c, fmt.Errorf("invalid profile label %q", label)
		}
		if _, ok := c.Accounts[id]; !ok {
			return c, fmt.Errorf("profile %q maps to unknown account", label)
		}
	}
	return c, nil
}

func selectAccount(c config, explicit, env string, envPresent bool) (string, error) {
	if explicit != "" {
		if _, ok := c.Accounts[explicit]; !ok {
			return "", fmt.Errorf("unknown account %q", explicit)
		}
		return explicit, nil
	}
	if !envPresent || env == "" {
		return c.DefaultAccount, nil
	}
	if !labelPattern.MatchString(env) {
		return "", fmt.Errorf("invalid DEVWHO_PROFILE label %q", env)
	}
	id, ok := c.Profiles[env]
	if !ok {
		return "", fmt.Errorf("DEVWHO_PROFILE %q has no account mapping", env)
	}
	return id, nil
}

func run(args []string, getenv func(string) (string, bool), stdout, stderr io.Writer) int {
	fs := flag.NewFlagSet("native-notes", flag.ContinueOnError)
	fs.SetOutput(stderr)
	configPath := fs.String("config", "", "app-owned JSON configuration")
	account := fs.String("account", "", "explicit app account id")
	if err := fs.Parse(args); err != nil {
		return 2
	}
	if *configPath == "" || fs.NArg() == 0 {
		fmt.Fprintln(stderr, "usage: native-notes --config PATH [--account ID] add TEXT | list | status")
		return 2
	}
	cmd := fs.Arg(0)
	if cmd != "add" && cmd != "list" && cmd != "status" {
		fmt.Fprintln(stderr, "command must be add, list, or status")
		return 2
	}
	if cmd == "add" && fs.NArg() != 2 {
		fmt.Fprintln(stderr, "add requires exactly one TEXT argument")
		return 2
	}
	if cmd != "add" && fs.NArg() != 1 {
		fmt.Fprintln(stderr, "list/status take no arguments")
		return 2
	}
	c, err := readConfig(*configPath)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	v, present := getenv("DEVWHO_PROFILE")
	selected, err := selectAccount(c, *account, v, present)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 1
	}
	storage := c.Accounts[selected]
	if !filepath.IsAbs(storage) {
		storage = filepath.Join(filepath.Dir(*configPath), storage)
	}
	if cmd == "status" {
		fmt.Fprintf(stdout, "account=%s\n", selected)
		return 0
	}
	if cmd == "add" {
		f, err := os.OpenFile(storage, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0600)
		if err != nil {
			fmt.Fprintf(stderr, "open notebook: %v\n", err)
			return 1
		}
		_, writeErr := fmt.Fprintln(f, fs.Arg(1))
		closeErr := f.Close()
		if writeErr != nil {
			fmt.Fprintf(stderr, "write notebook: %v\n", writeErr)
			return 1
		}
		if closeErr != nil {
			fmt.Fprintf(stderr, "close notebook: %v\n", closeErr)
			return 1
		}
		return 0
	}
	data, err := os.ReadFile(storage)
	if errors.Is(err, os.ErrNotExist) {
		return 0
	}
	if err != nil {
		fmt.Fprintf(stderr, "read notebook: %v\n", err)
		return 1
	}
	_, err = stdout.Write(data)
	if err != nil {
		fmt.Fprintf(stderr, "write output: %v\n", err)
		return 1
	}
	return 0
}

func main() { os.Exit(run(os.Args[1:], os.LookupEnv, os.Stdout, os.Stderr)) }
