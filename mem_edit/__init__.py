"""
mem_edit

mem_edit is a multi-platform (Windows and Linux) python package for
  reading, writing, and searching in the working memory of running
  programs.

To get started, try:

    from mem_edit import Process
    help(Process)

"""
import platform, os

from .utils import MemEditError


__author__ = 'Jan Petykiewicz'

from .VERSION import __version__
version = __version__       # legacy compatibility


system = platform.system()
if system == 'Windows':
    from .windows import Process
elif system == 'Linux':
    kv = os.uname().release.split(".")
    major, minor = int(kv[0]), int(kv[1])
    if (os.geteuid() == 0) and ((major > 3) or (major == 3 and minor >= 2)):
        from .linux_vm import Process
    else:
        from .linux import Process
else:
    raise MemEditError('Only Linux and Windows are currently supported.')
