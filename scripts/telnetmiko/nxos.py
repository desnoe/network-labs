from enum import Enum, auto, unique

from logzero import logger

from .base import LoggedTelnet


@unique
class Mode(Enum):
    UNKNWOWN = auto()
    POAP = auto()
    OPERATIONAL = auto()
    CONFIGURATION = auto()
    LOGGEDOUT = auto()


class Console(LoggedTelnet):
    TIMEOUT = 5
    MAX_TIMEOUTS = 10
    POAP_PROMPT_RE = r"\(yes/skip/no\)\[no\]: ".encode("ascii")
    OPER_PROMPT_RE = r"\w+\# $".encode("ascii")
    CONFIG_PROMPT_RE = r"\w+\(.*\)\# $".encode("ascii")
    LOGIN_PROMPT_RE = r" login: $".encode("ascii")
    BAD_USER_PASS_RE = b"Login incorrect"
    EXIT_DISCARD_RE = b"exit discard"

    def __init__(self, **kwargs):
        super(Console, self).__init__(**kwargs)
        self.mode = Mode.UNKNWOWN
        self.logged_in = None

    def skip_poap(self):
        command = "skip_poap"

        if self.mode is Mode.UNKNWOWN:
            self.expect_prompt(command=command)

        if self.mode is Mode.POAP:
            self.write_line('skip')
        else:
            raise Exception("Impossible to skip POAP!")

    def login(self, login="", password=""):
        command = "login"

        if self.mode is Mode.UNKNWOWN:
            self.expect_prompt(command=command)

        if self.mode is Mode.CONFIGURATION:
            self.configure(commit=False)  # exit configuration mode

        if self.mode is Mode.OPERATIONAL:
            self.logout()  # exit operational mode

        if self.mode is Mode.LOGGEDOUT:
            self.write_line(login)
            self.expect([b"Password:"])
            self.write_line(password)
            self.expect_prompt(command=command)
            self.send_command("terminal length 0")

        if self.mode is not Mode.OPERATIONAL:
            raise Exception("Impossible to log in!")

    def logout(self):
        command = "logout"

        if self.mode is Mode.CONFIGURATION:
            logger.debug(f"command={command}, sending exit")
            self.send_command("exit")

        if self.mode is Mode.OPERATIONAL:
            logger.debug(f"command={command}, sending exit")
            self.send_command("exit")

        if self.mode is Mode.LOGGEDOUT:
            return
        else:
            raise Exception("Impossible to log out!")

    def send_character(self, character, expect_prompt=True):
        self.write(character)
        if expect_prompt:
            self.expect_prompt("send_character")

    def send_command(self, command, expect_prompt=True):
        if self.mode not in (Mode.OPERATIONAL, Mode.CONFIGURATION):
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
                    self.POAP_PROMPT_RE,
                    self.OPER_PROMPT_RE,
                    self.CONFIG_PROMPT_RE,
                    self.LOGIN_PROMPT_RE,
                ],
                timeout=timeout,
            )
            count += 1
            logger.debug(f"command={command}, count={count}, expect result={str(r)}")

            if r[0] == 0:  # POAP prompt
                logger.debug(f"command={command}, count={count}, prompt is POAP")
                self.mode = Mode.POAP
            elif r[0] == 1:  # operational prompt
                logger.debug(f"command={command}, count={count}, prompt is OPERATIONAL")
                self.mode = Mode.OPERATIONAL
            elif r[0] == 2:  # configuration prompt
                logger.debug(f"command={command}, count={count}, prompt is CONFIGURATION")
                self.mode = Mode.CONFIGURATION
            elif r[0] == 3:  # login prompt
                logger.debug(f"command={command}, count={count}, prompt is LOGGEDOUT")
                self.mode = Mode.LOGGEDOUT
            elif r[0] == -1:  # Timeout
                self.mode = Mode.UNKNWOWN
                logger.debug(f"command={command}, count={count}, prompt is UNKNOWN")
                if len(r[2]) > 0:  # Data is flowing on the console, just loop and wait...
                    timeouts = 0
                    timeout = self.TIMEOUT
                else:  # Console does not seem to be responding, start sending control characters
                    timeouts += 1
                    timeout = timeouts * self.TIMEOUT
                logger.debug(f"command={command}, count={count}, timeouts={timeouts}, timeout={timeout}")

                if timeouts == 1:
                    self.write(b"\x03")  # send ctrl+C for the first control character
                    logger.debug(f"command={command}, count={count}, sending Ctrl+C")
                elif timeouts <= self.MAX_TIMEOUTS:
                    self.write_line()  # then try with enter because sometimes sending ctrl+C is not enough
                    logger.debug(f"command={command}, count={count}, sending Enter")
                else:
                    logger.debug(f"command={command}, count={count}, aborting!")
                    raise Exception("Impossible to get any prompt!")

            if self.mode is not Mode.UNKNWOWN:  # we do have a prompt
                return

    def configure(self, commands="", save=True):
        if self.mode is Mode.UNKNWOWN:
            self.expect_prompt("configure")

        if self.mode is Mode.LOGGEDOUT:
            raise Exception("You must first be logged in!")

        if self.mode is Mode.OPERATIONAL:
            self.send_command("configure")

        if self.mode is not Mode.CONFIGURATION:
            raise Exception("Impossible to get configuration prompt!")

        for command in commands.splitlines():
            self.send_command(command)

        self.send_command("exit")
        if save:
            self.send_command("copy running-config startup-config")

    def get_configuration(self):
        logline_index = len(self.loglines)
        self.configure(commands="show running-config", save=False)
        config_lines = self.loglines[logline_index + 4: -6]
        return "\n".join(config_lines)
