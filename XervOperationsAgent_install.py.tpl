#!/usr/bin/env python

import sys
import os
import platform
import fileinput
import urllib2
import urllib
import re
import urlparse
import socket

try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        print "Please update Python to version >= 2.6 or install python-simplejson!"
import subprocess
import logging
try: 
   from hashlib import md5
except ImportError:
   from md5 import md5

from optparse import OptionParser, make_option

DEBIAN_LIKE_SYSTEMS = ["Debian", "Mint", "Ubuntu"]
CENTOS_LIKE_SYSTEMS = ['CentOS Linux']
XOPS_2X_UBUNTU = "13.04"
XOPS_3X_UBUNTU = "13.10"
XOPS_2X_CENTOS_EL6 = "6.0"
XOPS_3X_CENTOS_EL7 = "7.0"

DEFAULT_INTERFACE = 'eth0'
TMP_DIR = '/tmp/'
URL_SCHEME = 'http'
URL_DOMAIN = 'xervmon.com'
URL_API_PATH = 'api/SystemMonitor'
URL_GET_PARAMS = {
        'key': 'X-API-KEY',
        'username': 'username',
        'host': 'host',
        'hostname': 'host_name'
        }

URL_METHODS = {
        'auth': 'authenticate',
        'enable': 'EnableHost'
        }

CUSTOMER_KEY = '${customer_key}'
TENANT = '${tenant}'

DEB_PACKAGE_2x = 'https://raw.githubusercontent.com/Xervmon/XIA/master/${agents_list}_2x_ubuntu'
DEB_PACKAGE_3x = 'https://raw.githubusercontent.com/Xervmon/XIA/master/${agents_list}_3x_ubuntu'
RPM_PACKAGE_EL5 = 'https://raw.githubusercontent.com/Xervmon/XIA/master/${agents_list}_2x_centos_el5'
RPM_PACKAGE_EL6 = 'https://raw.githubusercontent.com/Xervmon/XIA/master/${agents_list}_2x_centos_el6'
RPM_PACKAGE_EL7 = 'https://raw.githubusercontent.com/Xervmon/XIA/master/${agents_list}_3x_centos_el7'

AGENT_CONFIG = '/etc/puppet/puppet.conf'
DEFAULT_CONFIG="/etc/default/puppet"

DEB_XERVMON_REPO = "/etc/apt/sources.list.d/xervmon.list"
RPM_XERVMON_REPO = "/etc/yum.repos.d/xervmon.repo"

CONFIG = '''
# Copyright Xervmon inc.
[main]
logdir=/var/log/puppet
vardir=/var/lib/puppet
ssldir=/var/lib/puppet/ssl
rundir=/var/run/puppet
factpath=$$vardir/lib/facter
templatedir=$$confdir/templates
#prerun_command=/etc/puppet/etckeeper-commit-pre
#postrun_command=/etc/puppet/etckeeper-commit-post
server= ${xops_server}

[agent]
reports = true
node_name_value="%(server_key)s"
certname="%(server_key)s"

'''

PUP_DEFAULT = '''
# Defaults for puppet - sourced by /etc/init.d/puppet

# Start puppet on boot?
START=yes

# Startup options
DAEMON_OPTS=""
'''

DEB_REPO_CONFIG = '''
deb [arch=amd64] http://apt.xervmon.com %(dist_name)s contrib
'''

RPM_REPO_CONFIG = '''
[Xervmon]
name=Xervmon
baseurl=http://rpm.xervmon.com/$releasever/$basearch/
gpgcheck=0
enabled=1
'''

def get_interface_ip(ifname):
    import fcntl
    import struct
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(s.fileno(), 0x8915, struct.pack('256s',
                            ifname[:15]))[20:24])

def translate_params(params):
    params_url = {}
    if not isinstance(params, dict):
        return params_url
    for param_name, param_value in params.items():
        param = URL_GET_PARAMS.get(param_name)
        if param is None:
            # logger.error("No such param %s" % param_name)
            continue
        params_url[param] = param_value
    return params_url

def make_api_url(tenant, method, params=None):
    if tenant:
        netloc = '%s.%s' % (tenant, URL_DOMAIN)
    else: 
        netloc = URL_DOMAIN
    url_method = URL_METHODS.get(method)
    if url_method is None:
        return
    #url_path = urllib.basejoin(URL_API_PATH, url_method)
    url_path = URL_API_PATH + '/' + url_method
    params_url = translate_params(params)
    enc_params = urllib.urlencode(params_url)
    params = ''
    fragment = ''
    url = urlparse.urlunparse((URL_SCHEME, netloc, url_path, params,
        enc_params, fragment))
    print url
    return url


def check_ip(ip):
    # Check if given ip is valid
    if re.match(
            r'^(([0-1]?[0-9]{1,2}|25[0-5]|2[0-4][0-9])\.){3}([0-1]?[0-9]{1,2}|25[0-5]|2[0-4][0-9])$$',
            ip):
        return True
    return False


def make_api_call(tenant, api_method, params, method="GET"):
    api_key = params['key']
    import base64
    base64string = base64.encodestring('%s:%s' % ('omdadmin', 'omd')).replace('\n', '')
    headers = [('X-API-KEY', api_key), ("Authorization", "Basic %s" % base64string)]
    data = None
    if method == "POST":
        headers += [('Content-Type', 'application/json')]
        new_params = translate_params(params)
        #data = json.dumps(new_params)
        #params = None
    url = make_api_url(tenant, api_method, params)
    try:
        req = urllib2.Request(url, data, dict(headers))
        response = urllib2.urlopen(req)
    except urllib2.HTTPError:
        print 'Couldnt make an api call: %s. Please try another api key or contact our support'
        return
    try:
        return json.loads(response.read())
    except StandardError:
        return

def get_package_install_command(dist):
    if dist in DEBIAN_LIKE_SYSTEMS:
        command = "aptitude -q -y --allow-new-installs --safe-resolve install %s"
    else:
        command = "yum install -y %s"
    return command


def get_install_command(dist):
    if dist in DEBIAN_LIKE_SYSTEMS:
        command = "dpkg -i %s"
    else:
        command = "yum -y install %s"
    return command


def configure_xops_config(server_key, dist):
    added = False
    fp = open(AGENT_CONFIG, 'w')
    try:
        fp.write(CONFIG % dict(server_key=server_key.lower()))
    finally:
        fp.close()

def configure_xops_default():
    fp = open(DEFAULT_CONFIG, 'w')
    try:
        fp.write(PUP_DEFAULT)
    finally:
        fp.close()

def install_package(installer, package):
    command = installer % package
    # Legacy version due compatibility with Python <2.5
    p = subprocess.call(command, shell=True)
    #output, errors = p.communicate()
    #print "Errors: "+errors
    if p:
        return False
    else:
        return True

def install_list_of_packages(packages_url, dist_family):
    
    packages = urllib.urlopen(packages_url.rstrip())
    packages_list = packages.read()

    installer = get_package_install_command(dist_family)
    if not install_package(installer, packages_list):
        return False
    return True

def add_xervmon_repo(dist_family, dist_name):
    print dist_name
    if dist_family in DEBIAN_LIKE_SYSTEMS:
        repo_file_name = DEB_XERVMON_REPO
        repo_config =  DEB_REPO_CONFIG
        try:
            subprocess.call('apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 0C47D13D67E70387', shell=True)
            subprocess.call('gpg --export --armor 0C47D13D67E70387|apt-key add -', shell=True)
            subprocess.call('aptitude update', shell=True)
        except:
            print "Could not add repo key"
            return False
    else:
        repo_file_name = RPM_XERVMON_REPO
        repo_config =  RPM_REPO_CONFIG

    fp = open(repo_file_name, 'w')
    try:
        fp.write(repo_config % dict(dist_name=dist_name))
    finally:
        fp.close()
    return True

def install_xops(dist_family, dist_version, server_key):
    installed_epel = 0
    package_installer = get_package_install_command(dist_family)
    
    if dist_family in DEBIAN_LIKE_SYSTEMS:
        if dist_version < XOPS_3X_UBUNTU:
            if not install_package(package_installer, 'ruby facter libaugeas-ruby libxmlrpc-ruby libopenssl-ruby libshadow-ruby1.8'):
                return False
            if not install_list_of_packages(DEB_PACKAGE_2x, dist_family):
                return False
            configure_xops_default()
        elif dist_version >= XOPS_3X_UBUNTU:
            if not install_package(package_installer, 'ruby facter libaugeas-ruby ruby-shadow ruby-safe-yaml ruby-hiera'):
                return False
            if not install_list_of_packages(DEB_PACKAGE_3x, dist_family):
                return False
            try:
                subprocess.call('puppet agent --enable', shell=True)
            except:
                print "Could not enable agent"
                return False
        else:
            print "Unsupported version!"
            return False
    elif dist_family in CENTOS_LIKE_SYSTEMS:
        if not install_package(package_installer, 'ruby augeas-libs facter libselinux-ruby ruby-augeas ruby-shadow'):
            print "Going to add EPEL repository! Read https://fedoraproject.org/wiki/EPEL for details"
        installed_epel = 1
        if dist_version < XOPS_2X_CENTOS_EL6:
            if installed_epel == 1:
                try:
                    subprocess.call('rpm -Uvh http://dl.fedoraproject.org/pub/epel/5/x86_64/epel-release-5-4.noarch.rpm', shell=True)
                except:
                    print "ERROR: Can't add EPEl!"
                    return False
            if not install_list_of_packages(RPM_PACKAGE_EL5, dist_family):
                return False
        elif ( dist_version >= XOPS_2X_CENTOS_EL6 and dist_version < XOPS_3X_CENTOS_EL7 ):
            if installed_epel == 1:
                try:
                    subprocess.call('rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm', shell=True)
                except:
                    print "ERROR: Can't add EPEl!"
                    return False
            if not install_list_of_packages(RPM_PACKAGE_EL6, dist_family):
                return False
        elif dist_version >= XOPS_3X_CENTOS_EL7:
            if installed_epel == 1:
                try:
                    subprocess.call('rpm -Uvh http://dl.fedoraproject.org/pub/epel/beta/7/x86_64/epel-release-7-0.2.noarch.rpm', shell=True)
                except:
                    print "ERROR: Can't add EPEl!"
                    return False
            if not install_list_of_packages(RPM_PACKAGE_EL7, dist_family):
                return False
    else:
        print "Unsupported version!"
        return False
    configure_xops_config(server_key, dist_family)
    try:
        subprocess.call('/etc/init.d/puppet restart', shell=True)
    except:
        print "Couldnt start agent"
        return False

    return True


def get_from_input(msg):
    var = raw_input('%s\n' % msg)
    var = var.strip()
    return var


def main():
    #Main control function
    system = platform.system()
    # OLd function due to old python version in Centos 5 !!!
    # Must be platform.linux_distribution  since Python 2.6
    if platform.python_version() >= '2.6':
        dist_family = platform.linux_distribution()[0]
        dist_version = platform.linux_distribution()[1]
        dist_name = platform.linux_distribution()[2]
    else:
        dist_family = platform.dist()[0]
        dist_version = platform.dist()[1]
        dist_name = platform.dist()[2]
    if system != 'Linux':
        print ("We are sorry. We do not support %s. Currently support is only for Linux" % system)

    run_user = os.getenv("USER")
    if run_user != 'root':
        print 'Please run script as a root'

    usage = "usage: %prog [options]"
    option_list = [
            make_option("-u", "--user", action="store", type="string",
                dest="user", help="your portal's username"),
            make_option("-H", "--host", action="store", type="string",
                dest="host", help="host of the server. Please use -i if you want to detect interface ip"),
            make_option("-i", "--interface", action="store", type="string",
                dest="interface", help="default interface to detect ip if no host given", default=DEFAULT_INTERFACE),
            ]
    parser = OptionParser(usage, option_list=option_list)
    (options, args) = parser.parse_args()
    user = options.user
    host = options.host
    if host is not None and not check_ip(host):
        print "Please enter valid ip in host parameter."
        sys.exit()

    if host is None:
        try:
            host = get_interface_ip(options.interface)
        except StandardError:
            print 'Couldnt detect ip for interface %s' % options.interface
            sys.exit()
    if user is None:
        user = get_from_input("Enter your username")
    hostname = socket.gethostname()
    
    server_key = (TENANT+"-"+hostname+"-"+host).replace(".","-")
    print "Server key: "+server_key

    base_params = {'key': CUSTOMER_KEY, 'username': user}
    auth_res = make_api_call(TENANT, 'auth', base_params)
    if auth_res is None:
        print 'Error making auth api call'
        sys.exit(1)
    #if auth_res['status'] == 'error':
    #    print auth_res['error']
    #    sys.exit()
#    broker_ip = auth_res['broker_ip']
    res_add_repo = add_xervmon_repo(dist_family, dist_name)
    if not res_add_repo:
        print "Could not add required repository"
        sys.exit(1)

    res_install = install_xops(dist_family, dist_version, server_key)
    if not res_install:
        print "Couldnt install package"
        sys.exit(1)
    
    enable_params = base_params.copy()
    enable_params.update({'host': host, 'hostname': socket.gethostname()})
    enable_res = make_api_call(TENANT, 'enable', enable_params, "POST")
    print enable_res
    if enable_res is None or enable_res['status'] != 'success':
        print "Error enabling host"
        sys.exit()
    print "*** XervIntelligent Agent Successfully installed!"
    sys.exit()



if __name__ == '__main__':
    main()
