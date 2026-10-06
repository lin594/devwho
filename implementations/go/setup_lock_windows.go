//go:build setup && windows

package main

import "fmt"

func lockStore(path string) (func(), error) {
	return nil, fmt.Errorf("Configuration editor writes require a supported Unix platform")
}
