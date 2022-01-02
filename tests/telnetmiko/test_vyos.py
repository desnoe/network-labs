import unittest

import logzero

from scripts.telnetmiko.vyos import Console


class TestVyOS(unittest.TestCase):
    def test_all(self):  # TODO be totally rewritten
        fmt = "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs)03d %(module)s:%(lineno)d]%(end_color)s %(message)s"
        formatter = logzero.LogFormatter(fmt=fmt)
        logzero.formatter(formatter)

        v = Console(host="172.25.41.101", port=5105)
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


if __name__ == '__main__':
    unittest.main()
