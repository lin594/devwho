//go:build !windows

package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"syscall"
)

// Replace this process so children receive exactly their original argv, status,
// and signals. Resolve PATH from the target environment rather than our caller.
func executeChild(argv []string, env Env) (int, error) {
	file := argv[0]
	candidates := []string{file}
	if !strings.ContainsRune(file, '/') {
		candidates = []string{}
		path, ok := env["PATH"]
		if !ok {
			path = "/bin:/usr/bin"
		}
		dirs := filepath.SplitList(path)
		if path == "" {
			dirs = []string{""}
		}
		for _, dir := range dirs {
			if dir == "" {
				dir = "."
			}
			candidates = append(candidates, filepath.Join(dir, file))
		}
	}
	var firstError error
	for _, path := range candidates {
		e := syscall.Exec(path, argv, envList(env))
		if errors.Is(e, syscall.ENOENT) || (!strings.ContainsRune(file, '/') && errors.Is(e, syscall.ENOTDIR)) {
			continue
		}
		if firstError == nil {
			firstError = e
		}
	}
	if errors.Is(firstError, syscall.EACCES) {
		fmt.Fprintln(os.Stderr, "devwho: command is not executable")
		return 126, nil
	}
	if firstError != nil {
		return 1, fmt.Errorf("local operation failed (OSError)")
	}
	fmt.Fprintln(os.Stderr, "devwho: command not found")
	return 127, nil
}
