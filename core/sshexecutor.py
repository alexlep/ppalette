import socket
import paramiko
import os.path
import sys

host_key_file = os.path.expanduser('~/.ssh/known_hosts')
rsa_key_file = os.path.expanduser('~/.ssh/id_rsa')
ssh_connection_timeout = 4 # in seconds
'''
class HostUnit(object):
    def __init__(self, host, port=22):
        self.IP = host
        self.user = remote_system_user
        self.port = port
'''
class SSHConnection(object):
    def __init__(self, ipaddress, user, port = 22):
        if not (os.path.isfile(host_key_file)) or not (os.path.isfile(host_key_file)):
            print 'No host key file or no rsa key!'
            sys.exit(1)
        self.IP = ipaddress
        self.user = user
        self.port = port

    def establishSSHSession(self):
        if (not self.user) or (not self.IP): # if account is not found in the NEAC
            #self.logger.critical("Unable to fetch creds for %s (IP: %s). Check if NEAC contain account for service \"%s\"" % (ne.MO, ne.IP, ne.service))
            return False
        try:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys(host_key_file)
            self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
            self.rsa_key = paramiko.RSAKey.from_private_key_file(rsa_key_file)
            self.client.connect(self.IP, self.port, self.user, pkey = self.rsa_key, timeout = ssh_connection_timeout)
            self.channel = self.client.get_transport().open_session()
            #self.logger.info("Network Element %s: Authentication successfully done." % (ne.IP,))
            return True
        except Exception as err:
            #self.logger.info("Network Element %s is accessible. Continuing." % (ne.IP,))
            self.error = err
            return False


    def killSSHSession(self):
        return self.client.close()

    def executeCommand(self, command='/usr/bin/uptime'):
        if not self.establishSSHSession():
            res, details, exitcode = 'SSH connection failed: {}'.format(self.error), None, 2
        else:
            stdin, stdout, stderr = self.client.exec_command(command)
            exitcode = stdout.channel.recv_exit_status()
            if exitcode in range(0,3):
                output = stdout.read()
                try:
                    res, details = output.split('|')
                except:
                    res, details = output, None
            else:
                output = stderr.read()
                res, details = output, None
        self.killSSHSession()
        return [res, details, exitcode]
"""
host_unit = HostUnit(host = '10.88.59.65')#(host = '10.88.57.250')

commands = ('cat /proc/loadavg','which uptime', 'dsdsd')
for command in commands:
    conn = SSHConnection(host_unit)
    print conn.executeCommand(command)

conn = SSHConnection(host_unit)
print conn.executeCommand()
"""
