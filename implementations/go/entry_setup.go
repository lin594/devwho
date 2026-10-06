//go:build setup

package main

import (
	"fmt"
	"os"
)

func main() {
	code, e := setupArgs(os.Args[1:], os.Stdin, os.Stdout, os.Stderr)
	if e != nil {
		fmt.Fprintln(os.Stderr, "devwho-setup: "+e.Error())
		code = 1
	}
	os.Exit(code)
}
