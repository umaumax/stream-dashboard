#!/usr/bin/env python3

from streamlit_authenticator.utilities.hasher import Hasher

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('password')
    parser.add_argument('args', nargs='*')  # any length of args is ok

    args, extra_args = parser.parse_known_args()
    passwords_to_hash = [args.password]
    hashed_passwords = Hasher(passwords_to_hash).generate()
    for hashed_password in hashed_passwords:
        print(hashed_password)


if __name__ == '__main__':
    main()
