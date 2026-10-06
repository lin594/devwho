//go:build !setup

package main

import (
	"fmt"
	"os"
)

func main() {
	code, e := mainArgs(os.Args[1:])
	if e != nil {
		fmt.Fprintln(os.Stderr, "devwho: "+e.Error())
		code = 1
	}
	os.Exit(code)
}
