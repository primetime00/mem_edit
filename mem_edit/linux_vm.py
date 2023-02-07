"""
Implementation of Process class for Linux with kernel >= 3.2
"""

from typing import List, Tuple, Optional
from os import strerror
import os
import os.path
import signal
import ctypes
import ctypes.util
import logging

from .abstract import Process as AbstractProcess
from .utils import ctypes_buffer_t


logger = logging.getLogger(__name__)


def _error_checker(result, function, arguments):
    if result == -1:
        errno = ctypes.get_errno()
        raise OSError(errno, os.strerror(errno))

class IOBuffer(ctypes.Structure): # iovec struct
    _fields_ = [("base", ctypes.c_void_p),
                ("size", ctypes.c_size_t)]

_libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)
_read_process_memory = _libc.process_vm_readv
_read_process_memory.restype = ctypes.c_ssize_t
_read_process_memory.errcheck = _error_checker
_read_process_memory.args = [ctypes.c_ulong, ctypes.POINTER(IOBuffer),
                            ctypes.c_ulong, ctypes.POINTER(IOBuffer),
                            ctypes.c_ulong, ctypes.c_ulong]

_write_process_memory = _libc.process_vm_writev
_write_process_memory.restype = ctypes.c_ssize_t
_write_process_memory.errcheck = _error_checker
_write_process_memory.args = [ctypes.c_ulong, ctypes.POINTER(IOBuffer),
                            ctypes.c_ulong, ctypes.POINTER(IOBuffer),
                            ctypes.c_ulong, ctypes.c_ulong]

def read_process_memory(pid: int, base: int, buffer: ctypes_buffer_t) -> ctypes_buffer_t:
    size = ctypes.sizeof(buffer)
    local = IOBuffer(ctypes.addressof(buffer), size)
    remote = IOBuffer(base, size)
    res_size = _read_process_memory(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
    return buffer

def write_process_memory(pid: int, base: int, buffer: ctypes_buffer_t) -> ctypes_buffer_t:
    size = ctypes.sizeof(buffer)
    local = IOBuffer(ctypes.addressof(buffer), size)
    remote = IOBuffer(base, size)
    res_size = _write_process_memory(pid, ctypes.byref(local), 1, ctypes.byref(remote), 1, 0)
    return res_size

class Process(AbstractProcess):
    pid = None

    def __init__(self, process_id: int):
        self.pid = process_id

    def close(self):
        self.pid = None

    def write_memory(self, base_address: int, write_buffer: ctypes_buffer_t):
        write_process_memory(self.pid, base_address, write_buffer)

    def read_memory(self, base_address: int, read_buffer: ctypes_buffer_t) -> ctypes_buffer_t:
        return read_process_memory(self.pid, base_address, read_buffer)

    def get_path(self) -> str:
        try:
            with open('/proc/{}/cmdline', 'rb') as f:
                return f.read().decode().split('\x00')[0]
        except FileNotFoundError:
            return ''

    @staticmethod
    def list_available_pids() -> List[int]:
        pids = []
        for pid_str in os.listdir('/proc'):
            try:
                pids.append(int(pid_str))
            except ValueError:
                continue
        return pids

    @staticmethod
    def get_pid_by_name(target_name: str) -> Optional[int]:
        for pid in Process.list_available_pids():
            try:
                logger.debug('Checking name for pid {}'.format(pid))
                with open('/proc/{}/cmdline'.format(pid), 'rb') as cmdline:
                    path = cmdline.read().decode().split('\x00')[0]
            except FileNotFoundError:
                continue

            name = os.path.basename(path)
            logger.debug('Name was "{}"'.format(name))
            if path is not None and name == target_name:
                return pid

        logger.info('Found no process with name {}'.format(target_name))
        return None

    def list_mapped_regions(self, writeable_only: bool = True, include_paths = []) -> List[Tuple[int, int]]:
        regions = []
        with open('/proc/{}/maps'.format(self.pid), 'r') as maps:
            for line in maps:
                if "/dev/dri/" in line:
                    continue
                if "Proton" in line:
                    continue
                bounds, privileges = line.split()[0:2]

                if 'r' not in privileges:
                    continue

                if writeable_only and 'w' not in privileges:
                    continue

                start, stop = (int(bound, 16) for bound in bounds.split('-'))
                regions.append((start, stop))
        return regions
