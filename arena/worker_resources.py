"""Best-effort resource diagnostics; missing platform counters stay unknown."""
import os


def host_memory():
    try:
        if os.name=='nt':
            import ctypes
            from ctypes import wintypes
            class Memory(ctypes.Structure):
                _fields_=[('length',wintypes.DWORD),('load',wintypes.DWORD),
                          *[(name,ctypes.c_ulonglong) for name in ('total_physical','available_physical','total_commit','available_commit','total_virtual','available_virtual','extended_virtual')]]
            value=Memory();value.length=ctypes.sizeof(value)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):return {}
            return {'physical_total_bytes':value.total_physical,'physical_available_bytes':value.available_physical,
                    'commit_total_bytes':value.total_commit,'commit_available_bytes':value.available_commit,'memory_load_percent':value.load}
        if os.path.isfile('/proc/meminfo'):
            with open('/proc/meminfo') as stream:
                values={key:int(raw.split()[0])*1024 for line in stream for key,raw in [line.split(':',1)]}
            return {name:values[key] for name,key in [('physical_total_bytes','MemTotal'),('physical_available_bytes','MemAvailable'),('swap_total_bytes','SwapTotal'),('swap_available_bytes','SwapFree')] if key in values}
    except (OSError,ValueError,AttributeError):pass
    return {}


def process_cpu_seconds(process):
    # Popen retains the Windows process handle after wait, including on timeout.
    if os.name!='nt':
        try:
            with open('/proc/'+str(process.pid)+'/stat') as stream:fields=stream.read().rsplit(') ',1)[1].split()
            return (int(fields[11])+int(fields[12]))/os.sysconf('SC_CLK_TCK')
        except (OSError,ValueError,IndexError,AttributeError):return None
    try:
        import ctypes
        from ctypes import wintypes
        values=[wintypes.FILETIME() for _ in range(4)]
        function=ctypes.windll.kernel32.GetProcessTimes
        function.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
        function.restype=wintypes.BOOL
        if not function(wintypes.HANDLE(int(process._handle)),*[ctypes.byref(value) for value in values]):return None
        return sum((value.dwHighDateTime<<32)+value.dwLowDateTime for value in values[2:])/10_000_000
    except (OSError,ValueError,AttributeError):return None


def children_cpu_seconds():
    if os.name!='posix':return None
    import resource
    value=resource.getrusage(resource.RUSAGE_CHILDREN)
    return value.ru_utime+value.ru_stime


def log_tail(path, size=4096):
    try:
        with path.open('rb') as stream:
            stream.seek(0,2);stream.seek(max(0,stream.tell()-size))
            return stream.read(size).decode('utf-8',errors='replace')
    except OSError:return ''
