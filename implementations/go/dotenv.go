package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"unicode/utf8"
)

func dotenvError(line int) error     { return fmt.Errorf("Invalid dotenv assignment at line %d", line) }
func trimHorizontal(s string) string { return strings.Trim(s, " \t") }
func jsonQuotedEnd(s string) (int, error) {
	for i := 1; i < len(s); i++ {
		switch s[i] {
		case '"':
			return i + 1, nil
		case '\\':
			i++
			if i >= len(s) {
				return 0, fmt.Errorf("Invalid quoted value")
			}
			if s[i] != 'u' {
				if !strings.ContainsRune(`"\/bfnrt`, rune(s[i])) {
					return 0, fmt.Errorf("Invalid JSON escape")
				}
				continue
			}
			if i+4 >= len(s) {
				return 0, fmt.Errorf("Invalid Unicode escape")
			}
			n, e := strconv.ParseUint(s[i+1:i+5], 16, 16)
			if e != nil {
				return 0, e
			}
			i += 4
			if n >= 0xd800 && n <= 0xdbff {
				if i+6 >= len(s) || s[i+1] != '\\' || s[i+2] != 'u' {
					return 0, fmt.Errorf("Unpaired Unicode surrogate")
				}
				low, e := strconv.ParseUint(s[i+3:i+7], 16, 16)
				if e != nil || low < 0xdc00 || low > 0xdfff {
					return 0, fmt.Errorf("Unpaired Unicode surrogate")
				}
				i += 6
			} else if n >= 0xdc00 && n <= 0xdfff {
				return 0, fmt.Errorf("Unpaired Unicode surrogate")
			}
		}
	}
	return 0, fmt.Errorf("Unterminated quoted value")
}
func dotenvValue(raw string) (string, error) {
	left := strings.TrimLeft(raw, " \t")
	if strings.HasPrefix(left, "'") || strings.HasPrefix(left, `"`) {
		end := 0
		var value string
		if left[0] == '\'' {
			index := strings.IndexByte(left[1:], '\'')
			if index < 0 {
				return "", fmt.Errorf("Unterminated quoted value")
			}
			end = index + 2
			value = left[1 : end-1]
		} else {
			var e error
			end, e = jsonQuotedEnd(left)
			if e != nil {
				return "", e
			}
			if e = json.Unmarshal([]byte(left[:end]), &value); e != nil {
				return "", e
			}
		}
		suffix := trimHorizontal(left[end:])
		if suffix != "" && !strings.HasPrefix(suffix, "#") {
			return "", fmt.Errorf("Unexpected trailing text")
		}
		return value, nil
	}
	for i := 1; i < len(raw); i++ {
		if raw[i] == '#' && (raw[i-1] == ' ' || raw[i-1] == '\t') {
			raw = raw[:i]
			break
		}
	}
	return trimHorizontal(raw), nil
}
func parseDotenv(data []byte, explicit string) (*Profile, error) {
	if !utf8.Valid(data) || strings.ContainsRune(string(data), 0) {
		return nil, fmt.Errorf("Dotenv must be UTF-8 without NUL")
	}
	text := strings.ReplaceAll(string(data), "\r\n", "\n")
	if strings.ContainsRune(text, '\r') {
		return nil, fmt.Errorf("Dotenv contains a lone carriage return")
	}
	values := Env{}
	marker := ""
	markerSet := false
	for index, line := range strings.Split(text, "\n") {
		line = strings.TrimLeft(line, " \t")
		if trimHorizontal(line) == "" || strings.HasPrefix(line, "#") {
			continue
		}
		if strings.HasPrefix(line, "export ") {
			line = line[len("export "):]
		}
		key, raw, ok := strings.Cut(line, "=")
		key = trimHorizontal(key)
		if !ok || !envName.MatchString(key) {
			return nil, dotenvError(index + 1)
		}
		if _, ok := values[key]; ok || (key == "DEVWHO_PROFILE" && markerSet) {
			return nil, fmt.Errorf("Duplicate dotenv key: %s", key)
		}
		value, e := dotenvValue(raw)
		if e != nil || strings.ContainsRune(value, 0) {
			return nil, dotenvError(index + 1)
		}
		if key == "DEVWHO_PROFILE" {
			if !profileName.MatchString(value) {
				return nil, fmt.Errorf("Invalid dotenv profile marker")
			}
			marker = value
			markerSet = true
			continue
		}
		if e := validateEnv(key, false); e != nil {
			return nil, e
		}
		values[key] = value
	}
	if explicit != "" && !profileName.MatchString(explicit) {
		return nil, fmt.Errorf("Invalid dotenv profile name")
	}
	if markerSet && explicit != "" && marker != explicit {
		return nil, fmt.Errorf("Dotenv profile marker conflicts with --env-profile")
	}
	name := marker
	if explicit != "" {
		name = explicit
	}
	if name == "" {
		return nil, fmt.Errorf("Dotenv needs DEVWHO_PROFILE or --env-profile")
	}
	rawEnv := map[string]any{}
	for k, v := range values {
		rawEnv[k] = v
	}
	return parseProfile(name, map[string]any{"env": rawEnv}, nil)
}
func loadDotenv(path, profile string, env Env) (*Config, error) {
	selected, e := filepath.Abs(expandPath(path, env))
	if e != nil {
		return nil, e
	}
	if resolved, e := filepath.EvalSymlinks(selected); e == nil {
		selected = resolved
	}
	data, e := os.ReadFile(selected)
	if e != nil {
		return nil, fmt.Errorf("Cannot read dotenv configuration: %s", selected)
	}
	p, e := parseDotenv(data, profile)
	if e != nil {
		return nil, e
	}
	return &Config{Path: selected, Profiles: map[string]*Profile{p.Name: p}, Shortcut: p.Name, EnvFile: true}, nil
}
func exportDotenv(p *Profile) (string, error) {
	if len(p.Git) > 0 || len(p.SSH) > 0 || len(p.GitHub) > 0 || len(p.Unset) > 0 {
		return "", fmt.Errorf("Profile has semantic or unset settings; dotenv export would be lossy")
	}
	encode := func(v string) string { b, _ := json.Marshal(v); return string(b) }
	lines := []string{"DEVWHO_PROFILE=" + encode(p.Name)}
	for _, key := range sortedKeys(p.Env) {
		lines = append(lines, key+"="+encode(p.Env[key]))
	}
	return strings.Join(lines, "\n") + "\n", nil
}
