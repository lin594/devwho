//go:build windows

package main

import "fmt"

func executeChild(argv []string, env Env) (int, error) {
	return 1, fmt.Errorf("Windows process execution is unsupported; use Bash/Zsh on a supported Unix platform")
}
