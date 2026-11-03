"""POSIX worker launcher: set limits without preexec_fn in a threaded process."""
import os
import sys

if __name__=='__main__':
    import resource
    resource.setrlimit(resource.RLIMIT_FSIZE,(8_000_000,8_000_000))
    os.execvp(sys.argv[1],sys.argv[1:])
