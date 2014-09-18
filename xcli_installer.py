#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import subprocess
import string
import uuid

from optparse import OptionParser, make_option

xcli_config_name = "/etc/xcli/cli.modules.d/xops.yml"
repo_file_name = "/etc/apt/sources.list.d/xervmon.list"
repo_config = '''
deb [arch=amd64] http://apt.xervmon.com trusty contrib
'''

XCLI_CONFIG = '''
:xops:
  :enable_module: true
  :host: '%(xops_hostname)s'
  :username: '%(xopsuser)s'
  :password: '%(xopspsw)s'

  # Check cache status on each request
  #:refresh_cache: false

  # API request timeout, set -1 for infinity
  #:request_timeout: 120 #secondsq
'''


aptitude_command = "aptitude -q -y --allow-new-installs --safe-resolve install "
list_of_packages = "git xops-cli ruby-xcli ruby-xcli-xops"

def add_xervmon_repo():
	fp = open(repo_file_name, 'w')
	try:
		fp.write(repo_config)
	except:
		print "ERROR: Can't write file %s" % repo_file_name
		return False
	finally:
		fp.close()

	key = '0'
	try:
		key = subprocess.check_output('apt-key list|grep -c 67E70387', shell=True)
	except:
		print "INFO: Xervmon repository key not found"

	if key.rstrip() != '1':
		try:
			subprocess.check_call('apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 0C47D13D67E70387', shell=True)
		except:
			print "Any troubles during import xervmon key?"
	return True

def install_packages(list_of_packages):
	try:
		subprocess.check_call('aptitude update', shell=True)
		p = subprocess.check_call(aptitude_command+list_of_packages, shell=True)
	except:
		print "ERROR: Can't install packages %S " % list_of_packages
		return False
	return True

def configure_xcli_config(xops_hostname, xopsuser, xopspsw):
    added = False
    fp = open(xcli_config_name, 'w')
    try:
        fp.write(XCLI_CONFIG % dict(xops_hostname=xops_hostname.lower(), xopsuser=xopsuser, xopspsw=xopspsw))
    finally:
        fp.close()


def main():
	usage = "usage: %prog [options]"
	option_list = [
		make_option("-x", "--xopshostname", action="store", type="string",
			dest="xops_hostname", help="Full hostname (fqdn). Example: https://xops.xervmon.com"),
		make_option("-u", "--user", action="store", type="string",
			dest="xopsuser", help="XOPS admin username"),
		make_option("-p", "--password", action="store", type="string",
			dest="xopspsw", help="XOPS admin password"),
	]

	parser = OptionParser(usage, option_list=option_list)
	(options, args) = parser.parse_args()
	xops_hostname = options.xops_hostname

	xopsuser = options.xopsuser
	xopspsw = options.xopspsw

	if xops_hostname is None:
		print "Please enter XOPS hostname!"
		sys.exit(1)

	if xopsuser is None:
		print "Please enter XOPS admin username! Default: admin"
		sys.exit(1)
	if xopspsw is None:
		print "Please enter XOPS admin password! Default: changeme"
		sys.exit(1)

	res = add_xervmon_repo()
	if res is False:
		sys.exit(1)

	res = install_packages(list_of_packages)
	if res is False:
		sys.exit(1)

	res = configure_xcli_config(xops_hostname, xopsuser, xopspsw)
	if res is False:
		sys.exit(1)

	print "*********************************************"
	print "*********************************************"
	print "**                                         **"
	print "**      XCLI Installation complete !       **"
	print "**                                         **"
	print "*********************************************"
	print "*********************************************"


if __name__ == '__main__':
    main()
