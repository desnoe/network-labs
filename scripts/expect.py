import telnetlib
import logzero
from logzero import logger
from enum import Enum, auto, unique


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


@unique
class VyOSModes(Enum):
    UNKNWOWN = auto()
    OPERATIONAL = auto()
    CONFIGURATION = auto()
    LOGGEDOUT = auto()


class Vyos(LoggedTelnet):
    TIMEOUT = 3
    MAX_TIMEOUTS = 10
    OPER_PROMPT_RE = r"\w+@\w+:.+\$ $".encode("ascii")
    CONFIG_PROMPT_RE = r"\w+@\w+\# $".encode("ascii")
    LOGIN_PROMPT_RE = r"\w+ login: $".encode("ascii")
    BAD_USER_PASS_RE = b"Login incorrect"
    EXIT_DISCARD_RE = b"exit discard"

    def __init__(self, **kwargs):
        super(Vyos, self).__init__(**kwargs)
        self.mode = VyOSModes.UNKNWOWN
        self.logged_in = None

    def login(self, login="", password=""):
        command = "login"

        if self.mode is VyOSModes.UNKNWOWN:
            self.expect_prompt(command=command)

        if self.mode is VyOSModes.CONFIGURATION:
            self.configure(commit=False)  # exit configuration mode

        if self.mode is VyOSModes.OPERATIONAL:
            self.logout()  # exit operational mode

        if self.mode is VyOSModes.LOGGEDOUT:
            self.write_line(login)
            self.expect([b"Password:"])
            self.write_line(password)
            self.expect_prompt(command=command)
            self.send_command("set terminal length 0")

        if self.mode is not VyOSModes.OPERATIONAL:
            raise Exception("Impossible to log in!")

    def logout(self):
        command = "logout"

        if self.mode is VyOSModes.CONFIGURATION:
            self.send_command("exit discard")

        if self.mode is VyOSModes.OPERATIONAL:
            logger.debug(f"command={command}, sending Ctrl+D")
            v.send_character(b"\x04")

        if self.mode is VyOSModes.LOGGEDOUT:
            return
        else:
            raise Exception("Impossible to log out!")

    def send_character(self, character, expect_prompt=True):
        self.write(character)
        if expect_prompt:
            self.expect_prompt("send_character")

    def send_command(self, command, expect_prompt=True):
        if self.mode not in (VyOSModes.OPERATIONAL, VyOSModes.CONFIGURATION):
            raise Exception("Not logged in!")

        self.write_line(command)
        if expect_prompt:
            self.expect_prompt(command)

    def expect_prompt(self, command):
        timeout = self.TIMEOUT
        timeouts = 0
        count = 0
        while True:
            r = self.expect(
                [
                    self.OPER_PROMPT_RE,
                    self.CONFIG_PROMPT_RE,
                    self.LOGIN_PROMPT_RE,
                ],
                timeout=timeout,
            )
            count += 1
            logger.debug(f"command={command}, count={count}, expect result={str(r)}")

            if r[0] == 0:  # operational prompt
                logger.debug(f"command={command}, count={count}, prompt is OPERATIONAL")
                self.mode = VyOSModes.OPERATIONAL
            elif r[0] == 1:  # configuration prompt
                logger.debug(f"command={command}, count={count}, prompt is CONFIGURATION")
                self.mode = VyOSModes.CONFIGURATION
            elif r[0] == 2:  # login prompt
                logger.debug(f"command={command}, count={count}, prompt is LOGGEDOUT")
                self.mode = VyOSModes.LOGGEDOUT
            elif r[0] == -1:  # Timeout
                self.mode = VyOSModes.UNKNWOWN
                logger.debug(f"command={command}, count={count}, prompt is UNKNOWN")
                if len(r[2]) > 0:  # Data is flowing on the console, just loop and wait...
                    timeouts = 0
                    timeout = self.TIMEOUT
                else:  # Console does not seem to be responding, start sending control charaters
                    timeouts += 1
                    timeout = timeouts * self.TIMEOUT
                logger.debug(f"command={command}, count={count}, timeouts={timeouts}, timeout={timeout}")

                if timeouts == 1:
                    v.write(b"\x03")  # send ctrl+C for the first control character
                    logger.debug(f"command={command}, count={count}, sending Ctrl+C")
                elif timeouts <= self.MAX_TIMEOUTS:
                    v.write_line()  # then try with enter because sometimes sending ctrl+C is not enough
                    logger.debug(f"command={command}, count={count}, sending Enter")
                else:
                    logger.debug(f"command={command}, count={count}, aborting!")
                    raise Exception("Impossible to get any prompt!")

            if self.mode is not VyOSModes.UNKNWOWN:  # we do have a prompt
                return

    def configure(self, commands="", commit=True, save=True):
        if self.mode is VyOSModes.UNKNWOWN:
            self.expect_prompt("configure")

        if self.mode is VyOSModes.LOGGEDOUT:
            raise Exception("You must first be logged in!")

        if self.mode is VyOSModes.OPERATIONAL:
            self.send_command("configure")

        if self.mode is not VyOSModes.CONFIGURATION:
            raise Exception("Impossible to get configuration prompt!")

        for command in commands.splitlines():
            self.send_command(command)

        if commit:
            self.send_command("commit")
            if save:
                self.send_command("save")
            self.send_command("exit")
        else:
            self.send_command("exit discard")

    def get_configuration(self, commands=False, json=False):
        logline_index = len(self.loglines)
        if commands:
            self.configure(commands="show | commands", commit=False)
        elif json:
            self.configure(commands="show | json", commit=False)
        else:
            self.configure(commands="show", commit=False)
        config_lines = self.loglines[logline_index + 3 : -4]
        return "\n".join(config_lines)


fmt = "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs)03d %(module)s:%(lineno)d]%(end_color)s %(message)s"
formatter = logzero.LogFormatter(fmt=fmt)
logzero.formatter(formatter)

v = Vyos(host="172.25.41.101", port=5105)
v.login("vyos", "vyos")
v.login("vyos", "vyos")
v.configure(commit=False)
v.login("vyos", "vyos")
print(v.get_configuration())
print(v.get_configuration(commands=True))
print(v.get_configuration(json=True))
v.logout()
v.login("vyos", "vyos")
v.logout()
