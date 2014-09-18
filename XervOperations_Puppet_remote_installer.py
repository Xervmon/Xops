#!/usr/bin/env python
#
# Example:
# ./XervOperations_Puppet_remote_installer.py --host 104.131.36.111 --user root --password ****** -x testauomation.xervmon.com -m ******* --githubuser *****@mail.com --githubpassword ***** -l US -o Xervmon
#
import socket, sys
from optparse import OptionParser, make_option
try:  
    import libssh2
except ImportError:
    print "INFO: python-libssh2 required! Trying to install..."
    try:
        subprocess.check_call('aptitude -q -y --allow-new-installs --safe-resolve install python-libssh2', shell=True)
    except:
        print "ERROR: Can't install required python-libssh2! Exit..."
        sys.exit(2)
  
DEBUG=False 
def my_print(args):
    if DEBUG: print(args)
  
class SSHRemoteClient(object):
    def __init__(self, hostname, username, password, port=22):
        self.username = username
        self.password = password
        self.hostname = hostname
        self.port = port
  
        self.session = libssh2.Session()
        self.session.set_banner()
  
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.hostname,self.port))
            self.session.startup(sock)
            my_print(self.session.last_error())
            self.session.userauth_password(self.username,self.password)
            my_print(self.session.last_error())
        except Exception, e:
            print str(e)
            raise Exception, self.session.last_error()
  
        self.channel = self.session.open_session()
        my_print(self.session.last_error())
  
    def execute(self, command="uname -a"):
        buffer = 4096
        rc = self.channel.execute(command)
        my_print(rc)
        while True:
            data = self.channel.read(buffer)
            if data == '' or data is None: break
            my_print(type(data))
            print data.strip()
  
        self.channel.close()
  
    def __del__(self):
        self.session.close()
        my_print(self.session.last_error())

class MySCPClient:
    def __init__(self, hostname, username, password, port=22):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self._prepare_sock()
  
    def _prepare_sock(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.hostname, self.port))
            self.sock.setblocking(1)
        except Exception, e:
            print "SockError: Can't connect socket to %s:%d" % (self.hostname, self.port)
            print e
  
        try:
            self.session = libssh2.Session()
            self.session.set_banner()
            self.session.startup(self.sock)
            self.session.userauth_password(self.username, self.password)
        except Exception, e:
            print "SSHError: Can't startup session"
            print e
  
    def send(self, remote_path, mode=0644):
        datas=""
        f=file(remote_path, "rb")
        while True:
            data = f.readline()
            if  len(data) == 0: 
                break
            else:
                datas += data
        file_size = len(datas)
        channel = self.session.scp_send(remote_path, mode, file_size)
        channel.write(datas)
        channel.close()
  
    def __del__(self):
        self.session.close()
        self.sock.close()


def main():
    usage = "usage: %prog [options]"
    option_list = [
        make_option("--host", action="store", type="string",
            dest="target_host", help="Target remote host to install XOPS"),
        make_option("-u", "--user", action="store", type="string",
            dest="target_host_user", help="User on target remote host to install XOPS(root)"),
        make_option("-p", "--password", action="store", type="string",
            dest="target_host_password", help="User password on target remote host to install XOPS"),
        make_option("-x", "--xopshostname", action="store", type="string",
            dest="xops_hostname", help="Full hostname (fqdn). Example: xops.xervmon.com"),
        make_option("-m", "--mysql-password", action="store", type="string",
            dest="mysqlpsw", help="MySQL admin password"),
        make_option("--githubuser", action="store", type="string",
            dest="githubuser", help="GitHub username"),
        make_option("--githubpassword", action="store", type="string",
            dest="githubpassword", help="GitHub user password"),
        make_option("-l", "--location", action="store", type="string",
            dest="xops_location", help="Location for XOPS"),
        make_option("-o", "--organization", action="store", type="string",
            dest="xops_organization", help="Organization for XOPS"),
        make_option("-s", "--xopsproxy", action="store", type="string",
            dest="xops_proxy", help="XOPS smart proxy address"),
    ]

    parser = OptionParser(usage, option_list=option_list)
    (options, args) = parser.parse_args()
    target_host = options.target_host
    target_host_user = options.target_host_user
    target_host_password = options.target_host_password
    xops_hostname = options.xops_hostname
    mysqluser = "root"
    mysqlpsw = options.mysqlpsw
    githubuser = options.githubuser
    githubpassword = options.githubpassword
    xops_location = options.xops_location
    xops_organization = options.xops_organization
    xops_proxy = options.xops_proxy

    if target_host is None:
        print "Please enter remote target host!"
        sys.exit(1)
    if target_host_user is None:
        print "Please enter user on remote target host with superuser rights!"
        sys.exit(1)
    if target_host_password is None:
        print "Please enter user password on remote target host with superuser rights!"
        sys.exit(1)        
    if mysqlpsw is None:
        print "Please enter MySQL admin password!"
        sys.exit(1)
    if githubuser is None:
        print "Please enter username for GitHub!"
        sys.exit(1)
    if githubpassword is None:
        print "Please enter user password for GitHub!"
        sys.exit(1)

#   Copying to remote host XervOperations_Puppet_installer.py
    try:
        myscp = MySCPClient(target_host, target_host_user, target_host_password )
        myscp.send("XervOperations_Puppet_installer.py")
    except Exception, e:
        print "ERROR: Can't copy XervOperations_Puppet_installer.py to target remote host!"
        print str(e)
        sys.exit(1)
    except KeyboardInterrupt, e:
        sys.exit(1)


#   Installing mysql-server on remote host
#   Preparing, entering mysql root crdentials
    try:
        src = SSHRemoteClient(target_host, target_host_user, target_host_password)
        src.execute("echo 'machine github.com \nlogin "+githubuser+"\npassword "+githubpassword+"' >>~/.netrc&& chmod 600 ~/.netrc")
    except Exception, e:
        print str(e)
    except KeyboardInterrupt, e:
        sys.exit(1)        

    try:
        src = SSHRemoteClient(target_host, target_host_user, target_host_password)
   src.execute("echo 'mysql-server mysql-server/root_password password "+mysqlpsw+"'|debconf-set-selections; echo 'mysql-server mysql-server/root_password_again password "+mysqlpsw+"'|debconf-set-selections")
    except Exception, e:
        print str(e)
    except KeyboardInterrupt, e:
        sys.exit(1)

    try:
        src = SSHRemoteClient(target_host, target_host_user, target_host_password)
   src.execute("/usr/bin/apt-get -y install mysql-server")
    except Exception, e:
        print str(e)
    except KeyboardInterrupt, e:
        sys.exit(1)

    try:
        src = SSHRemoteClient(target_host, target_host_user, target_host_password)
        src.execute("/etc/init.d/mysql start")
    except Exception, e:
        print str(e)
    except KeyboardInterrupt, e:
        sys.exit(1)

    try:
        src = SSHRemoteClient(target_host, target_host_user, target_host_password)
        src.execute("echo '[client]\npassword="+mysqlpsw+"'>~/.my.cnf")
    except Exception, e:
        print str(e)
    except KeyboardInterrupt, e:
        sys.exit(1)


    try:
        src = SSHRemoteClient(target_host, target_host_user, target_host_password)
        src.execute("python XervOperations_Puppet_installer.py -x "+xops_hostname+" -u root -p '"+mysqlpsw+"' -l "+xops_location+" -o"+xops_organization)
    except Exception, e:
        print str(e)
    except KeyboardInterrupt, e:
        sys.exit(1)



if __name__ == '__main__':
    main()
