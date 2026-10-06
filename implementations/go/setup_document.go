//go:build setup

package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"strconv"
	"strings"
	"unicode/utf8"

	"github.com/pelletier/go-toml/v2"
)

type Document struct {
	Data   map[string]any
	Orders map[string][]string
}

func parseDocumentTOML(raw []byte) (*Document, error) {
	var d map[string]any
	if e := toml.Unmarshal(raw, &d); e != nil {
		return nil, fmt.Errorf("Invalid TOML configuration")
	}
	orders, e := runtimeOrders(raw)
	if e != nil {
		return nil, fmt.Errorf("Invalid TOML configuration")
	}
	if _, e = validateDocument(d, "", orders); e != nil {
		return nil, e
	}
	return &Document{d, orders}, nil
}
func strictJSONStringScalars(raw []byte) error {
	if !utf8.Valid(raw) {
		return fmt.Errorf("Configuration JSON must be UTF-8")
	}
	for i := 0; i < len(raw); i++ {
		if raw[i] == '"' {
			end, e := jsonQuotedEnd(string(raw[i:]))
			if e != nil {
				return fmt.Errorf("Invalid JSON string or Unicode escape")
			}
			i += end - 1
		}
	}
	return nil
}
func parseDocumentJSON(raw []byte) (*Document, error) {
	if len(raw) > 1024*1024 {
		return nil, fmt.Errorf("Configuration JSON exceeds its size limit")
	}
	if e := strictJSONStringScalars(raw); e != nil {
		return nil, e
	}
	dec := json.NewDecoder(bytes.NewReader(raw))
	dec.UseNumber()
	orders := map[string][]string{}
	var read func([]string) (any, error)
	read = func(path []string) (any, error) {
		token, e := dec.Token()
		if e != nil {
			return nil, e
		}
		switch v := token.(type) {
		case json.Delim:
			switch v {
			case '{':
				m := map[string]any{}
				for dec.More() {
					tok, e := dec.Token()
					if e != nil {
						return nil, e
					}
					key, ok := tok.(string)
					if !ok {
						return nil, fmt.Errorf("Invalid JSON key")
					}
					if _, ok := m[key]; ok {
						return nil, fmt.Errorf("Duplicate JSON key")
					}
					if len(path) == 4 && path[0] == "profiles" && path[2] == "git" && path[3] == "config" {
						orders[path[1]] = append(orders[path[1]], key)
					}
					value, e := read(append(append([]string{}, path...), key))
					if e != nil {
						return nil, e
					}
					m[key] = value
				}
				if end, e := dec.Token(); e != nil || end != json.Delim('}') {
					return nil, fmt.Errorf("Invalid JSON object")
				}
				return m, nil
			case '[':
				a := []any{}
				for dec.More() {
					item, e := read(path)
					if e != nil {
						return nil, e
					}
					a = append(a, item)
				}
				if end, e := dec.Token(); e != nil || end != json.Delim(']') {
					return nil, fmt.Errorf("Invalid JSON array")
				}
				return a, nil
			}
			return nil, fmt.Errorf("Invalid JSON structure")
		case json.Number:
			if !strings.ContainsAny(v.String(), ".eE") {
				if n, e := strconv.ParseInt(v.String(), 10, 64); e == nil {
					return n, nil
				}
			}
			return v, nil
		default:
			return token, nil
		}
	}
	v, e := read(nil)
	if e != nil {
		return nil, fmt.Errorf("Invalid configuration JSON: %s", safeJSONError(e))
	}
	if _, e := dec.Token(); e != io.EOF {
		return nil, fmt.Errorf("Configuration JSON must contain one document")
	}
	d, ok := v.(map[string]any)
	if !ok {
		return nil, fmt.Errorf("Configuration must be a JSON object")
	}
	if _, e := validateDocument(d, "", orders); e != nil {
		return nil, e
	}
	return &Document{d, orders}, nil
}
func safeJSONError(e error) string {
	switch e.Error() {
	case "Duplicate JSON key", "Invalid JSON key", "Invalid JSON object", "Invalid JSON array", "Invalid JSON structure":
		return e.Error()
	}
	return "invalid syntax"
}
func orderedJSON(v any, path []string, orders map[string][]string) string {
	switch x := v.(type) {
	case map[string]any:
		keys := sortedKeys(x)
		if len(path) == 4 && path[0] == "profiles" && path[2] == "git" && path[3] == "config" {
			keys = orderedKeys(x, orders[path[1]])
		}
		parts := []string{}
		for _, k := range keys {
			b, _ := json.Marshal(k)
			parts = append(parts, string(b)+":"+orderedJSON(x[k], append(append([]string{}, path...), k), orders))
		}
		return "{" + strings.Join(parts, ",") + "}"
	case []any:
		a := []string{}
		for _, item := range x {
			a = append(a, orderedJSON(item, path, orders))
		}
		return "[" + strings.Join(a, ",") + "]"
	default:
		b, _ := json.Marshal(v)
		return string(b)
	}
}
func orderedKeys(m map[string]any, order []string) []string {
	keys := []string{}
	seen := map[string]bool{}
	for _, k := range order {
		if _, ok := m[k]; ok && !seen[k] {
			keys = append(keys, k)
			seen[k] = true
		}
	}
	for _, k := range sortedKeys(m) {
		if !seen[k] {
			keys = append(keys, k)
		}
	}
	return keys
}
func redactDocument(doc *Document) *Document {
	next := &Document{deepCopyValue(doc.Data).(map[string]any), doc.Orders}
	profiles := next.Data["profiles"].(map[string]any)
	for _, v := range profiles {
		p := v.(map[string]any)
		if env, ok := p["env"].(map[string]any); ok {
			for k := range env {
				env[k] = "<redacted>"
			}
		}
		if git, ok := p["git"].(map[string]any); ok {
			if conf, ok := git["config"].(map[string]any); ok {
				for k, v := range conf {
					if a, ok := v.([]any); ok {
						redacted := []any{}
						for range a {
							redacted = append(redacted, "<redacted>")
						}
						conf[k] = redacted
					} else {
						conf[k] = "<redacted>"
					}
				}
			}
		}
	}
	return next
}
func tomlString(s string) string {
	var b strings.Builder
	b.WriteByte('"')
	for _, r := range s {
		switch r {
		case '"':
			b.WriteString(`\"`)
		case '\\':
			b.WriteString(`\\`)
		case '\n':
			b.WriteString(`\n`)
		case '\r':
			b.WriteString(`\r`)
		case '\t':
			b.WriteString(`\t`)
		case '\b':
			b.WriteString(`\b`)
		case '\f':
			b.WriteString(`\f`)
		default:
			if r < 0x20 || r == 0x7f {
				fmt.Fprintf(&b, `\u%04X`, r)
			} else {
				b.WriteRune(r)
			}
		}
	}
	b.WriteByte('"')
	return b.String()
}
func tomlValue(v any) string {
	switch x := v.(type) {
	case string:
		return tomlString(x)
	case bool:
		return strconv.FormatBool(x)
	case int64:
		return strconv.FormatInt(x, 10)
	case []any:
		a := []string{}
		for _, v := range x {
			a = append(a, tomlValue(v))
		}
		return "[" + strings.Join(a, ", ") + "]"
	}
	panic("unvalidated TOML value")
}
func renderDocumentTOML(doc *Document) ([]byte, error) {
	if _, e := validateDocument(doc.Data, "", doc.Orders); e != nil {
		return nil, e
	}
	var b strings.Builder
	b.WriteString("version = 1\n")
	if s, ok := doc.Data["settings"].(map[string]any); ok {
		b.WriteString("\n[settings]\n")
		for _, k := range sortedKeys(s) {
			fmt.Fprintf(&b, "%s = %s\n", k, tomlValue(s[k]))
		}
	}
	profiles := doc.Data["profiles"].(map[string]any)
	for _, name := range sortedKeys(profiles) {
		p := profiles[name].(map[string]any)
		prefix := "profiles." + tomlString(name)
		fmt.Fprintf(&b, "\n[%s]\n", prefix)
		if v, ok := p["unset_env"]; ok {
			fmt.Fprintf(&b, "unset_env = %s\n", tomlValue(v))
		}
		for _, section := range []string{"git", "git_ssh", "github", "env"} {
			m, ok := p[section].(map[string]any)
			if !ok {
				continue
			}
			fmt.Fprintf(&b, "\n[%s.%s]\n", prefix, section)
			for _, k := range sortedKeys(m) {
				if k == "config" && section == "git" {
					continue
				}
				fmt.Fprintf(&b, "%s = %s\n", tomlString(k), tomlValue(m[k]))
			}
			if section == "git" {
				if runtime, ok := m["config"].(map[string]any); ok {
					fmt.Fprintf(&b, "\n[%s.git.config]\n", prefix)
					for _, k := range orderedKeys(runtime, doc.Orders[name]) {
						fmt.Fprintf(&b, "%s = %s\n", tomlString(k), tomlValue(runtime[k]))
					}
				}
			}
		}
	}
	return []byte(b.String()), nil
}

func deepCopyValue(v any) any {
	switch x := v.(type) {
	case map[string]any:
		r := map[string]any{}
		for k, v := range x {
			r[k] = deepCopyValue(v)
		}
		return r
	case []any:
		r := []any{}
		for _, v := range x {
			r = append(r, deepCopyValue(v))
		}
		return r
	default:
		return v
	}
}
