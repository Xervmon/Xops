#!/usr/bin/env python

import sys
import os
import fileinput
import hashlib
import string
from optparse import OptionParser, make_option

import zipfile

DEFAULT_TENANT = 'app'
AGENT_FILENAME = 'XervOperationsAgent_install.py'
DEFAULT_AGENT_TEMPLATE = './'+AGENT_FILENAME+'.tpl'
DEFAULT_AGENT_DST_DIR = './'
DEFAULT_TMP_DIR = '/tmp'
DEFAULT_XOPS_SERVER = "xops.xervmon.com"

def agent_install_prepare(customer_key, tenant, agent_template, agent_dst_dir, temp_dir, xops_server, agents_list):
	with open(agent_template, 'r') as ft:
		agent_template = string.Template(ft.read())

	with open(temp_dir+'/'+AGENT_FILENAME, 'w') as fp:
		fp.write(agent_template.safe_substitute( dict(customer_key=customer_key, tenant=tenant, xops_server=xops_server, agents_list=agents_list)))
	
	with zipfile.ZipFile(agent_dst_dir+'/'+AGENT_FILENAME+'.zip', mode='w') as zf:
		zf.write(temp_dir+'/'+AGENT_FILENAME,AGENT_FILENAME)


def main():
	usage = "usage: %prog [options]"
	option_list = [
		make_option("-k", "--key", action="store", type="string",
			dest="key", help="Customer API key (X-API-KEY)"),
		make_option("-t", "--tenant", action="store", type="string",
			dest="tenant", default=DEFAULT_TENANT,
			help="tenant to our api service. Should appear in customers dashboard"),
		make_option("-i","--input", action="store", type="string",
			dest="agent_template", help="agent template", default=DEFAULT_AGENT_TEMPLATE),
		make_option("-o", "--output", action="store", type="string",
			dest="agent_dst_dir", help="output directory for agent", default=DEFAULT_AGENT_DST_DIR),
		make_option("-d", "--tempdir", action="store", type="string",
			dest="temp_dir", help="output directory for agent", default=DEFAULT_TMP_DIR),
		make_option("-m", "--masterserver", action="store", type="string",
			dest="xops_server", help="Hostname of XOPS master server", default=DEFAULT_XOPS_SERVER),
		make_option("-x", "--monitoringagent", action="store", type="string",
			dest="monitoring_agent", help="Install monitoring agent? (yes)", default='yes'),
		make_option("-g", "--manageagent", action="store", type="string",
			dest="manage_agent", help="Install management agent? (yes)", default='yes'),
	]
	parser = OptionParser(usage, option_list=option_list)
	(options, args) = parser.parse_args()
	customer_key = options.key
	tenant = options.tenant
	agent_template = options.agent_template
	agent_dst_dir = options.agent_dst_dir
	temp_dir = options.temp_dir
	xops_server = options.xops_server
	monitoring_agent = options.monitoring_agent
	manage_agent = options.manage_agent

	if customer_key is None:
		print "Please enter Customer API key (X-API-KEY)!"
		sys.exit(1)
	if not os.path.isfile(agent_template):
		print "Can not find template file "+agent_template
		sys.exit(1)
	if not os.path.exists(agent_dst_dir):
		print "Can not find directory "+agent_dst_dir
		sys.exit(1)
	if not os.path.exists(temp_dir):
		print "Can't find temp dir "+temp_dir+" , trying to use default "+DEFAULT_TMP_DIR
		temp_dir = DEFAULT_TMP_DIR
	print "Used Tenant: "+tenant

	print "monitoring_agent: "+monitoring_agent
	print "manage_agent: "+manage_agent
	if ( monitoring_agent == "yes" and manage_agent == "yes"):
		agents_list = "xia_n_mgmt"
	elif ( monitoring_agent == "no" and manage_agent == "yes"):
		agents_list = "mgmt"
	elif ( monitoring_agent == "yes" and manage_agent == "no"):
		agents_list = "xia"
	else:
		print "ERROR: One of the agents must be installed! (monitoring_agent or manage_agent)"
		sys.exit(1)
	
	agent_install_prepare( customer_key, tenant, agent_template, agent_dst_dir, temp_dir, xops_server, agents_list)

if __name__ == '__main__':
    main()
