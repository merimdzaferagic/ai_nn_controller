# Copyright (c) 2026 Trinity College Dublin
#
# This file is dual-licensed:
# - under the AGPL (see LICENSE)
# - under a commercial licence (contact infoknex@tcd.ie)

from pathlib import Path
from time import monotonic, sleep
from .config import vprint


def check_entropy():
    timeout_s = 60.0
    entropytarget = 70#160
    entropyfile = Path('/proc/sys/kernel/random/entropy_avail')
    assert entropyfile.is_file()

    start = monotonic()
    while True:
        entropy = int(entropyfile.read_text().strip())
        if entropy > entropytarget:
            vprint('Kernel available entropy at {}, which is > {}'.format(
                    entropy,
                    entropytarget,
                )
            )
            break

        if monotonic() > start + timeout_s:
            raise TimeoutError(
                'Available entropy never reached {} bytes or more '
                'after {:.2f}. Last read value was {}.'.format(
                    entropytarget,
                    timeout_s,
                    entropy,
                )
            )

        vprint(
            'Not enough entropy available in the Linux kernel, '
            'This Software requires at least {} bytes. '
            'Current value is {}. '
            'Startup will be delayed for 5 seconds in hope of gathering '
            'more entropy.'.format(
                entropytarget,
                entropy,
            )
        )
        sleep(5)
