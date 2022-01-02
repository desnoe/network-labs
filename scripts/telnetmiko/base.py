import telnetlib


class LoggedTelnet(telnetlib.Telnet):
    def __init__(self, **kwargs):
        super(LoggedTelnet, self).__init__(**kwargs)
        self.logbytes = b""
        self.loglines = []

    def _log(self, s):
        self.logbytes += s
        self.logbytes = self.logbytes.replace(b"\r\r", b"\r")
        self.loglines = self.logbytes.decode().splitlines()

    def expect(self, regex_list, timeout=None):
        r = super(LoggedTelnet, self).expect(regex_list, timeout)
        self._log(r[2])
        return r

    def read_very_lazy(self):
        s = super(LoggedTelnet, self).read_very_lazy()
        self._log(s)
        return s

    def read_all(self) -> bytes:
        s = super(LoggedTelnet, self).read_all()
        self._log(s)
        return s

    def read_some(self) -> bytes:
        s = super(LoggedTelnet, self).read_some()
        self._log(s)
        return s

    def read(self):
        return self.read_very_eager()

    def write(self, s):
        if isinstance(s, str):
            s = s.encode(encoding="ascii")
        return super(LoggedTelnet, self).write(s)

    def write_line(self, s=""):
        if isinstance(s, str):
            s = s.encode(encoding="ascii")
        return self.write(s + b"\n")
