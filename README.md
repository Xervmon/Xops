Preq
- apt-get install git facter mysql-server

=======
*** How to xia_puppet_installer.py <- XIA, Mysql and Puppetmaster located on same server!
For other read below section xia_installer.py


Before executing xia_puppet_installer.py make sure:
- You have installed mysql-server - need to provide admin(root) db user credentials
- You have installed facter. If not execute: aptitude install facter

- Run xia_puppet_installer.py
  Example: xia_puppet_installer.py -x xiaserver1.xervmon.com -u root -p 1qaz
  where -x is full hostname(even fake, but NOT IP) -u mysql db admin -p mysql db password
  After few minutes you'll be asked about your credentials for github.com - required to clone repository

  Then open XIA web interface in your browser https://xia.xervmon.com/smart_proxies (change xia.xervmon to actual XIA hostname)
  Press "New Smart Proxy", add the Name: "Puppet-Proxy" and URL: http://xia.xervmon.com:8443 (must be the same host where xia-proxy and puppetmaster installed)
  In case of same server use http://127.0.0.1:8443


*** How to xia_installer.py
Before executing xia_installer.py make sure:

- You have properly installed mysql and new database created, plus special user added
  Example to create DB and user, run mysql client:
  CREATE DATABASE xia CHARACTER SET utf8;
  CREATE USER 'xia'@'localhost' IDENTIFIED BY 'somepassword';
  GRANT ALL PRIVILEGES ON xia.* TO 'xia'@'localhost';

- Host has set full domainname
  to check run 'facter fqdn', and in case of empty output add line with domain to /etc/hosts
  Example:
  127.0.0.1 testxia.xervmon.com testxia

- Run xia_install.py
  Example:
  python xia_installer.py --host localhost -d xia -u xia -p somepassword

- Install puppetmaster on any reachable server (or localhost) and xia-proxy package on same host
  Configure puppet master. Example of configuration with few modules could be cloned from https://github.com/sseshachala/XervPaaS/tree/master/XIA/XIA-Master
  On puppet master server copy all files and directories FROM inside cloned copy to /etc/puppet/:

  cd XervPaaS/XIA/XIA-Master/ 
  cp -rf ./* /etc/puppet/

  Update /etc/puppet/puppet.conf - replace xia.xervmon.com with present hostname. Here you setting host for puppetmaster
  Same for /etc/puppet/node.rb - NB "SETTINGS = {:url          =>" must be pointed to XIA web interface. By default https://xia.xervmon.com, add port in case of non-standard, for example http://107.170.137.21:3000. Here you setting host(and probably port) for XIA

- After installing XIA, do not forget to configure smart-proxy
  Edit /etc/xia-proxy/settings.yml
  Add trusted hosts and enable puppet feature in place in config:
  
  :trusted_hosts:
  - localhost
  - xia.xervmon.com
  # enable PuppetCA management
  :puppetca: true
  
  # enable Puppet management
  :puppet: true
  :puppet_conf: /etc/puppet/puppet.conf
  
- On XIA server. Update apache site config /etc/apache2/sites-enabled/05-xia-ssl.conf - change xia.xervmon.com to actual hostname and reload apache2 service  

  Then open XIA web interface in your browser https://xia.xervmon.com/smart_proxies (change xia.xervmon to actual XIA hostname)
  Press "New Smart Proxy", add the Name: "Puppet-Proxy" and URL: http://xia.xervmon.com:8443 (must be the same host where xia-proxy and puppetmaster installed)
  In case of same server use http://127.0.0.1:8443
