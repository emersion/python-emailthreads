#!/usr/bin/env python3

from distutils.core import setup
import subprocess
import os

ver = os.environ.get("PKGVER")

if not ver:
	subp = subprocess.run(['git', 'describe', '--tags'],
		stdout=subprocess.PIPE)
	if subp.returncode != 0:
		ver = "0.0.0"
	else:
		ver = subp.stdout.decode().strip()

setup(
	name = 'emailthreads',
	packages = [
		'emailthreads',
	],
	version = ver,
	description = 'Parses email threads into conversation trees',
	author = 'Simon Ser',
	author_email = 'contact@emersion.fr',
	url = 'https://github.com/emersion/python-emailthreads',
	license = 'MIT'
)
