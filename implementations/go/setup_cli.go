//go:build setup

package main

import (
	"encoding/json"
	"fmt"
	"io"
	"path/filepath"
	"strings"
)

const setupHelp = `Usage: devwho-setup [--config PATH] [--language en|zh-CN] COMMAND
Commands: read [--show-values], replace --if-revision HASH|missing, configure
With no command, start the interactive configuration form.
The editor writes standard TOML; it does not activate profiles.
`

func setupArgs(args []string, in io.Reader, out, errOut io.Writer) (int, error) {
	path, language := "", "en"
	usage := func(s string) (int, error) { fmt.Fprintln(errOut, "devwho-setup: "+s); return 2, nil }
	for len(args) > 0 {
		a := args[0]
		if a == "--help" || a == "-h" {
			fmt.Fprint(out, setupHelp)
			return 0, nil
		}
		if a == "--version" {
			fmt.Fprintln(out, "devwho-setup "+version)
			return 0, nil
		}
		key, value, inline := strings.Cut(a, "=")
		if key != "--config" && key != "--language" {
			break
		}
		if inline {
			args = args[1:]
		} else {
			if len(args) < 2 {
				return usage(key + " requires a value")
			}
			value = args[1]
			args = args[2:]
		}
		if key == "--config" {
			path = value
		} else {
			language = value
		}
	}
	if language != "en" && language != "zh-CN" {
		return usage("--language requires en or zh-CN")
	}
	env := environment()
	if path == "" {
		path = configPath(env)
	}
	selected, e := filepath.Abs(expandPath(path, env))
	if e != nil {
		return 1, e
	}
	command := "configure"
	if len(args) > 0 {
		command = args[0]
		args = args[1:]
	}
	switch command {
	case "read":
		show := false
		if len(args) == 1 && args[0] == "--show-values" {
			show = true
		} else if len(args) != 0 {
			return usage("read accepts only --show-values")
		}
		stored, e := storeRead(selected)
		if e != nil {
			return 1, e
		}
		configuration := "null"
		if stored.Document != nil {
			doc := stored.Document
			if !show {
				doc = redactDocument(doc)
			}
			configuration = orderedJSON(doc.Data, nil, doc.Orders)
		}
		rev, _ := json.Marshal(stored.Revision)
		fmt.Fprintf(out, "{\"revision\":%s,\"configuration\":%s,\"redacted\":%t}\n", rev, configuration, !show)
		return 0, nil
	case "replace":
		expected := ""
		if len(args) == 2 && args[0] == "--if-revision" {
			expected = args[1]
		} else if len(args) == 1 && strings.HasPrefix(args[0], "--if-revision=") {
			expected = strings.TrimPrefix(args[0], "--if-revision=")
		} else {
			return usage("replace requires --if-revision HASH or missing")
		}
		raw, e := io.ReadAll(io.LimitReader(in, 1024*1024+1))
		if e != nil {
			return 1, fmt.Errorf("Cannot read replacement JSON")
		}
		doc, e := parseDocumentJSON(raw)
		if e != nil {
			return 1, e
		}
		stored, e := storeSave(selected, doc, expected)
		if e != nil {
			return 1, e
		}
		fmt.Fprintf(out, "{\"revision\":%q}\n", stored.Revision)
		return 0, nil
	case "configure":
		if len(args) != 0 {
			return usage("configure accepts no arguments")
		}
		return configureForm(selected, language, in, out)
	default:
		return usage("unknown command")
	}
}
