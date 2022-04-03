import unittest

import logzero

from scripts.telnetmiko.nxos import Console, Mode


class TestNXOS(unittest.TestCase):
    def test_all(self):  # TODO be totally rewritten
        fmt = "%(color)s[%(levelname)1.1s %(asctime)s.%(msecs)03d %(module)s:%(lineno)d]%(end_color)s %(message)s"
        formatter = logzero.LogFormatter(fmt=fmt)
        logzero.formatter(formatter)

        v = Console(host="gns3.lab.aws.delarche.fr", port=5006)
        # v.expect_prompt(command='skip_poap')
        # if v.mode == Mode.POAP:
        #     v.skip_poap()

        v.login("admin", "")
        v.configure(save=False)
        print('-')
        print(v.get_configuration())
        print('-')
        v.logout()

        # v.login("vyos", "vyos")
        # v.configure(commit=False)
        # v.login("vyos", "vyos")
        # print(v.get_configuration())
        # print(v.get_configuration(commands=True))
        # print(v.get_configuration(json=True))
        # v.logout()
        # v.login("vyos", "vyos")
        # v.logout()


if __name__ == '__main__':
    unittest.main()
