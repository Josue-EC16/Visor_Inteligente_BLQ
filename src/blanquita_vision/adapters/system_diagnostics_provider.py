import platform
import sys


class SystemDiagnosticsProvider:
    def snapshot(self) -> dict:
        return dict(app_version="0.1.0", python=sys.version.split()[0], os=platform.system(),
                    architecture=platform.machine(), cpu_usage=None, ram_usage=None, gpu_usage=None)
