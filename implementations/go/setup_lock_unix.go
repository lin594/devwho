//go:build setup && !windows

package main

import (
	"fmt"
	"os"
	"syscall"
)

func lockStore(path string) (func(), error) {
	fd, e := syscall.Open(path, syscall.O_CREAT|syscall.O_RDWR|syscall.O_CLOEXEC|syscall.O_NOFOLLOW, 0600)
	if e != nil {
		return nil, fmt.Errorf("Cannot open safe configuration lock")
	}
	file := os.NewFile(uintptr(fd), path)
	info, e := file.Stat()
	if e != nil || !info.Mode().IsRegular() {
		file.Close()
		return nil, fmt.Errorf("Configuration lock must be a regular file")
	}
	if e = file.Chmod(0600); e != nil {
		file.Close()
		return nil, fmt.Errorf("Cannot make configuration lock private")
	}
	if e = syscall.Flock(fd, syscall.LOCK_EX); e != nil {
		file.Close()
		return nil, fmt.Errorf("Cannot lock configuration")
	}
	return func() { syscall.Flock(fd, syscall.LOCK_UN); file.Close() }, nil
}
