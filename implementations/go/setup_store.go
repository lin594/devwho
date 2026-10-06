//go:build setup

package main

import (
	"crypto/sha256"
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

type Stored struct {
	Revision string
	Document *Document
	Raw      []byte
}

func revision(raw []byte) string { return fmt.Sprintf("%x", sha256.Sum256(raw)) }
func storeReadRaw(path string) (*Stored, error) {
	raw, e := os.ReadFile(path)
	if errors.Is(e, os.ErrNotExist) {
		return &Stored{Revision: "missing"}, nil
	}
	if e != nil {
		return nil, fmt.Errorf("Cannot read configuration")
	}
	return &Stored{Revision: revision(raw), Raw: raw}, nil
}
func storeRead(path string) (*Stored, error) {
	stored, e := storeReadRaw(path)
	if e != nil || stored.Revision == "missing" {
		return stored, e
	}
	doc, e := parseDocumentTOML(stored.Raw)
	if e != nil {
		return nil, e
	}
	stored.Document = doc
	return stored, nil
}
func regularPath(path string, allowMissing bool) error {
	info, e := os.Lstat(path)
	if allowMissing && errors.Is(e, os.ErrNotExist) {
		return nil
	}
	if e != nil {
		return fmt.Errorf("Cannot inspect local configuration path")
	}
	if !info.Mode().IsRegular() {
		return fmt.Errorf("Configuration writes require a regular file; symlinks are rejected")
	}
	return nil
}
func privateBackup(path string, raw []byte, rev string) (string, error) {
	dir := filepath.Join(filepath.Dir(path), ".devwho-backups")
	if e := os.Mkdir(dir, 0700); e != nil && !errors.Is(e, os.ErrExist) {
		return "", e
	}
	info, e := os.Lstat(dir)
	if e != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
		return "", fmt.Errorf("Backup directory must be a real directory")
	}
	if e = os.Chmod(dir, 0700); e != nil {
		return "", e
	}
	f, e := os.CreateTemp(dir, rev+"-*.toml")
	if e != nil {
		return "", e
	}
	if e = f.Chmod(0600); e != nil {
		f.Close()
		os.Remove(f.Name())
		return "", e
	}
	backup := f.Name()
	ok := false
	defer func() {
		f.Close()
		if !ok {
			os.Remove(backup)
		}
	}()
	if _, e = f.Write(raw); e != nil {
		return "", e
	}
	if e = f.Sync(); e != nil {
		return "", e
	}
	if e = f.Close(); e != nil {
		return "", e
	}
	if e = syncDirectory(dir); e != nil {
		return "", e
	}
	ok = true
	return backup, nil
}
func syncDirectory(path string) error {
	f, e := os.Open(path)
	if e != nil {
		return e
	}
	defer f.Close()
	return f.Sync()
}

// One CAS path serves both machine replacement and the interactive editor.
// The persistent flock sidecar coordinates DevWho editors; external tools that
// ignore that lock can still race with a save.
func storeSave(path string, doc *Document, expected string) (*Stored, error) {
	raw, e := renderDocumentTOML(doc)
	if e != nil {
		return nil, e
	}
	if expected != "missing" {
		if len(expected) != 64 {
			return nil, fmt.Errorf("Invalid revision")
		}
		for _, c := range expected {
			if !(c >= '0' && c <= '9') && !(c >= 'a' && c <= 'f') {
				return nil, fmt.Errorf("Invalid revision")
			}
		}
	}
	if e = os.MkdirAll(filepath.Dir(path), 0700); e != nil {
		return nil, fmt.Errorf("Cannot create configuration directory")
	}
	unlock, e := lockStore(path + ".lock")
	if e != nil {
		return nil, e
	}
	defer unlock()
	if e = regularPath(path, true); e != nil {
		return nil, e
	}
	current, e := storeReadRaw(path)
	if e != nil {
		return nil, e
	}
	if current.Revision != expected {
		return nil, fmt.Errorf("Configuration revision changed; reread before saving")
	}
	if current.Revision != "missing" {
		if _, e = privateBackup(path, current.Raw, current.Revision); e != nil {
			return nil, fmt.Errorf("Cannot create private configuration backup")
		}
	}
	f, e := os.CreateTemp(filepath.Dir(path), ".devwho-config-*.tmp")
	if e != nil {
		return nil, fmt.Errorf("Cannot create private configuration temporary file")
	}
	if e = f.Chmod(0600); e != nil {
		f.Close()
		os.Remove(f.Name())
		return nil, fmt.Errorf("Cannot make configuration temporary file private")
	}
	temp := f.Name()
	defer os.Remove(temp)
	if _, e = f.Write(raw); e == nil {
		e = f.Sync()
	}
	ce := f.Close()
	if e != nil || ce != nil {
		return nil, fmt.Errorf("Cannot write configuration temporary file")
	}
	if e = regularPath(path, true); e != nil {
		return nil, e
	}
	if e = os.Rename(temp, path); e != nil {
		return nil, fmt.Errorf("Cannot atomically replace configuration")
	}
	if e = syncDirectory(filepath.Dir(path)); e != nil {
		return nil, fmt.Errorf("Configuration saved but directory sync failed")
	}
	return &Stored{revision(raw), doc, raw}, nil
}
