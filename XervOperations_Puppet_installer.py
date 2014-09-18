#!/usr/bin/python
# -*- coding: UTF-8 -*-

import os
import sys
import subprocess
import string
import uuid
from time import sleep
from optparse import OptionParser, make_option

repo_file_name = "/etc/apt/sources.list.d/xervmon.list"
repo_config = '''
deb [arch=amd64] http://apt.xervmon.com trusty contrib
'''

uuid = uuid.uuid4()

mysqlhost = "localhost"
xopsdb = "xops"
xopsdbuser = "xops"
xopsdbpsw = uuid.hex 
# "Zhzhzh"	# TBD

database_config_file_name = "/etc/xops/database.yml"
database_config = '''
production:
  adapter: mysql2
  database: %(mysqldb)s
  username: %(mysqluser)s
  password: %(mysqlpsw)s
  host: %(mysqlhost)s
'''

xops_default_config_file_name = "/etc/default/xops"

xops_default_config = '''
# Start xops on boot?
START=no

# the location where xops is installed
#XOPS_HOME=/usr/share/xops

# the network interface which xops web server is running at
#XOPS_IFACE=0.0.0.0

# the port which xops web server is running at
# note that if the xops user is not root, it has to be a > 1024
# For non-root port 80, consider using Apache+Passenger
#XOPS_PORT=3000

# the user which runs the web interface
XOPS_USER=xops

# the rails environment in which xops runs
XOPS_ENV=production
'''

aptitude_command = "aptitude -q -y --allow-new-installs --safe-resolve install "
list_of_packages = "apache2 libapache2-mod-passenger git xops xops-mysql2 puppetmaster xops-proxy xops-console xops-compute xops-assets xops-cli ruby-hammer-cli ruby-hammer-cli-xops ruby-xops-api xops-gce xops-libvirt xops-vmware"


puppetconf_github = "https://github.com/sseshachala/XervPaaS.git"
puppetconf_s3 = "http://xervmon-xops.s3.amazonaws.com/xops.tar.gz"
puppetconf_dstdir = "/root/XervPassInstall"
puppetconf_path = "XOPS/XOPS-Master"

xopsproxy_path = "XOPS/XOPS-Proxy/settings.yml"
xopsreport_path = "XOPS/XOPS-Reports/xops.rb"
xopsapache_path = "XOPS/XOPS-Apache/05-xops-ssl.conf"
xopsconf_path = "XOPS/XOPS-Conf/settings.yaml"


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

def add_database_config(mysqlhost, xopsdb, xopsdbuser, xopsdbpsw):
	fp = open(database_config_file_name, 'w')
	try:
		fp.write(database_config % dict(mysqlhost=mysqlhost, mysqldb=xopsdb, mysqluser=xopsdbuser, mysqlpsw=xopsdbpsw))
	except:
		print "ERROR: Can't write file %s" % database_config_file_name
		return False
	finally:
		fp.close()
	return True

def add_xops_default_config():
	fp = open(xops_default_config_file_name, 'w')
	try:
		fp.write(xops_default_config)
	except:
		print "ERROR: Can't write file %s" % xops_default_config
		return False
	finally:
		fp.close()
	return True

def xops_db_init(mysqlhost, mysqluser, mysqlpsw, xopsdb, xopsdbuser, xopsdbpsw):
	try:
		fqdn = subprocess.check_output("facter fqdn", shell=True)
	except:
		print "ERROR: Can't check FQDN!"
		return False

	if fqdn == "":
		print "ERROR: Full domain name required! Please add it to /etc/hosts"
		return False

	try:
		subprocess.check_call('mysql -h '+mysqlhost+' -u '+mysqluser+' -p'+mysqlpsw+' -e "CREATE DATABASE '+xopsdb+' CHARACTER SET utf8;"', shell=True)
	except:
		print "ERROR: Can't create DB for XOPS!"
		return False

	try:
		subprocess.check_call('mysql -h '+mysqlhost+' -u '+mysqluser+' -p'+mysqlpsw+' -e "CREATE USER \''+xopsdbuser+'\'@\'localhost\' IDENTIFIED BY \''+xopsdbpsw+'\';"', shell=True)
	except :
		print "ERROR: Can't create DB user for XOPS!"
		return False

	try:
		subprocess.check_call('mysql -h '+mysqlhost+' -u '+mysqluser+' -p'+mysqlpsw+' -e "GRANT ALL PRIVILEGES ON '+xopsdb+'.* TO \''+xopsdbuser+'\'@\'localhost\';"', shell=True)
	except:
		print "ERROR: Can't grant privileges xops user for XOPS DB!"
		return False


	try:
		subprocess.check_call('xops-rake db:migrate', shell=True)
	except:
		print "ERROR: Can't create xops database structure! Check mysql connection, credentials and DB existence"
		return False

	try:
		subprocess.check_call('xops-rake db:seed', shell=True)
	except:
		print "ERROR: Can't fill xops database! Check full domain name of the server with 'facter fqdn'"
		return False
	return True

def clone_puppet_config():
	print "*********************************************"
	print "*********************************************"
	print "**                                         **"
	print "**     Enter your github credentials !     **"
	print "**                                         **"
	print "*********************************************"
	print "*********************************************"
	try:
		subprocess.check_call('git clone '+puppetconf_github+' '+puppetconf_dstdir, shell=True)
	except:
		print "ERROR: Can't clone puppetmaster configuration!"
		return False

	try:
		subprocess.check_call('cp -rf '+puppetconf_dstdir+'/'+puppetconf_path+'/* /etc/puppet/', shell=True)
	except:
		print "ERROR: Can't copy puppet configuration to /etc/puppet"

	return True

def get_puppet_config():
	if not os.path.exists(puppetconf_dstdir):
		try:
			os.makedirs(puppetconf_dstdir)
		except:
			print "ERROR: Can't create directory"
			return False
	try:
		subprocess.check_call('wget -P '+puppetconf_dstdir+' '+puppetconf_s3, shell=True)
	except:
		print "ERROR: Can't clone puppetmaster configuration!"
		return False

	try:
		subprocess.check_call('tar -C '+puppetconf_dstdir+' -xzf *.tar.gz', shell=True)
	except:
		print "ERROR: Can't untar puppetmaster configuration!"
		return False

	try:
		subprocess.check_call('cp -rf '+puppetconf_dstdir+'/'+puppetconf_path+'/* /etc/puppet/', shell=True)
	except:
		print "ERROR: Can't copy puppet configuration to /etc/puppet"

	return True


####### Hardcode :(

def init_configs(xops_hostname):
	with open(puppetconf_dstdir+'/'+puppetconf_path+'/node.rb', 'r') as nt:
		node_template = string.Template(nt.read())

	with open('/etc/puppet/node.rb', 'w') as np:
		np.write(node_template.safe_substitute( dict(xops_hostname=xops_hostname)))

	with open(puppetconf_dstdir+'/'+puppetconf_path+'/puppet.conf', 'r') as pt:
		puppetconf_template = string.Template(pt.read())

	with open('/etc/puppet/puppet.conf', 'w') as pp:
		pp.write(puppetconf_template.safe_substitute( dict(xops_hostname=xops_hostname)))

	with open(puppetconf_dstdir+'/'+xopsconf_path, 'r') as xct:
		xopsconf_template = string.Template(xct.read())

	with open('/etc/xops/settings.yaml', 'w') as xcp:
		xcp.write(xopsconf_template.safe_substitute(dict(xops_hostname=xops_hostname)))

	with open(puppetconf_dstdir+'/'+xopsproxy_path, 'r') as prt:
		xopsproxy_template = string.Template(prt.read())

	with open('/etc/xops-proxy/settings.yml', 'w') as prp:
		prp.write(xopsproxy_template.safe_substitute( dict(xops_hostname=xops_hostname)))

	with open(puppetconf_dstdir+'/'+xopsreport_path, 'r') as xt:
		xopsreport_template = string.Template(xt.read())

	with open('/usr/lib/ruby/vendor_ruby/puppet/reports/xops.rb', 'w') as xp:
		xp.write(xopsreport_template.safe_substitute( dict(xops_hostname=xops_hostname)))

	with open(puppetconf_dstdir+'/'+xopsapache_path, 'r') as at:
		xopsapache_template = string.Template(at.read())

	with open('/etc/apache2/sites-available/05-xops-ssl.conf', 'w') as ap:
		ap.write(xopsapache_template.safe_substitute( dict(xops_hostname=xops_hostname)))

	try:
		subprocess.check_call('rm -f /etc/apache2/sites-enabled/000-default.conf', shell=True)
	except:
		print "INFO: Default apache config not found"

	try:
		subprocess.check_call('/etc/init.d/puppetmaster stop', shell=True)
	except:
		print "ERROR: Can't stop puppetmaster service!"
		return False

	sleep(2)
	try:
		subprocess.check_call('/etc/init.d/puppetmaster start', shell=True)
	except:
		print "ERROR: Can't start puppetmaster service!"
		return False

	try:
		subprocess.check_call('/etc/init.d/xops-proxy restart', shell=True)
	except:
		print "ERROR: Can't restart xops-proxy service!"
		return False

	try:
		subprocess.check_call('/etc/init.d/apache2 restart', shell=True)
	except:
		print "ERROR: Can't restart Apache2 service!"
		return False

	return True
def xops_location_add(xops_location):
	try:
		subprocess.check_call('xops-rake apipie:cache', shell=True)
		subprocess.check_call('hammer location create --name '+xops_location, shell=True)
	except:
		print "ERROR: Can't add new location to XOPS!"
		return False
	return True

def xops_organization_add(xops_organization):
	try:
		subprocess.check_call('hammer organization create --name '+xops_organization, shell=True)
	except:
		print "ERROR: Can't add new organization to XOPS!"
		return False
	return True

def xops_proxy_add(xops_proxy):
	try:
		subprocess.check_call('hammer proxy create --name XOPS-Proxy --url '+xops_proxy, shell=True)
	except:
		print "ERROR: Can't add new smart proxy to XOPS!"
		return False
	return True

def xops_puppet_classes_import():
	try:
		subprocess.check_call('hammer proxy import-classes --id 1', shell=True)
	except:
		print "ERROR: Can't import new puppet classes to XOPS!"
		return False
	return True

def xops_add_default_settings():
	try:
		subprocess.check_call('hammer domain create --name xervmon.com', shell=True)
	except:
		print "ERROR: Can't add default domain xervmon.com to XOPS!"
		return False
	try:
		subprocess.check_call('hammer hostgroup create --environment-id 1 --domain-id 1 --name default --puppet-ca-proxy-id 1 --puppet-proxy-id 1', shell=True)
	except:
		print "ERROR: Can't add default hostgroup to XOPS!"
		return False
	return True


def main():
	usage = "usage: %prog [options]"
	option_list = [
		make_option("-x", "--xopshostname", action="store", type="string",
			dest="xops_hostname", help="Full hostname (fqdn). Example: xops.xervmon.com"),
		make_option("-u", "--user", action="store", type="string",
			dest="mysqluser", help="MySQL admin username"),
		make_option("-p", "--password", action="store", type="string",
			dest="mysqlpsw", help="MySQL admin password"),
		make_option("-l", "--location", action="store", type="string",
			dest="xops_location", help="Location for XOPS"),
		make_option("-o", "--organization", action="store", type="string",
			dest="xops_organization", help="Organization for XOPS"),
		make_option("-s", "--xopsproxy", action="store", type="string",
			dest="xops_proxy", help="XOPS smart proxy address"),
	]

	parser = OptionParser(usage, option_list=option_list)
	(options, args) = parser.parse_args()
	xops_hostname = options.xops_hostname
	try:
		fqdn = subprocess.check_output("facter fqdn", shell=True)
	except:
		print "INFO: Utility facter required. Trying to install..."
		try:
			subprocess.check_call('aptitude -q -y --allow-new-installs --safe-resolve install facter', shell=True)
			fqdn = subprocess.check_output("facter fqdn", shell=True)
		except:
			print "ERROR: Can't check FQDN! Can't install facter! Please try to run: aptitude install facter"
			sys.exit(1)

	if fqdn == "":
		if xops_hostname is None:
			print "ERROR: Full domain name required! Please use --xopshostname options or add it to /etc/hosts"
			sys.exit(1)
		else:
			with open("/etc/hosts",'r+') as f:
				content = f.read()
				f.seek(0,0)
				f.write("127.0.0.1\t"+xops_hostname+' '+xops_hostname.split('.')[0]+'\n' + content)


	mysqluser = options.mysqluser
	mysqlpsw = options.mysqlpsw
	xops_location = options.xops_location
	xops_organization = options.xops_organization
	xops_proxy = options.xops_proxy

	if mysqluser is None:
		print "Please enter MySQL admin username!"
		sys.exit(1)
	if mysqlpsw is None:
		print "Please enter MySQL admin password!"
		sys.exit(1)

	res = add_xervmon_repo()
	if res is False:
		sys.exit(1)

	res = install_packages(list_of_packages)
	if res is False:
		sys.exit(1)

	res = add_database_config(mysqlhost, xopsdb, xopsdbuser, xopsdbpsw)
	if res is False:
		sys.exit(1)

	res = xops_db_init(mysqlhost, mysqluser, mysqlpsw, xopsdb, xopsdbuser, xopsdbpsw)
	if res is False:
		sys.exit(1)

	res = add_xops_default_config()
	if res is False:
		sys.exit(1)

	res = get_puppet_config()
	if res is False:
		sys.exit(1)

	res = init_configs(xops_hostname)
	if res is False:
		sys.exit(1)

	if xops_location is not None:
		res = xops_location_add(xops_location)
		if res is False:
			sys.exit(1)

	if xops_organization is not None:
		res = xops_organization_add(xops_organization)
		if res is False:
			sys.exit(1)

	if xops_proxy is None:
		xops_proxy = "http://127.0.0.1:8443"
	res = xops_proxy_add(xops_proxy)
	if res is False:
		sys.exit(1)

	res = xops_puppet_classes_import()
	if res is False:
		sys.exit(1)

	res = xops_add_default_settings()
	if res is False:
		sys.exit(1)

	print "*********************************************"
	print "*********************************************"
	print "**                                         **"
	print "**         XOPS Operations Center           **"
	print "**         Installation complete !         **"
	print "**                                         **"
	print "*********************************************"
	print "*********************************************"


if __name__ == '__main__':
    main()
