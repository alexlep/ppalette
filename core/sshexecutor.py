# -*- coding: utf-8 -*-
import paramiko

class SSHConnection(object):

    def __init__(self, ipaddress, user, ssh_config, port=22):
        self.host_key_file = ssh_config.host_key_file
        self.rsa_key_file = ssh_config.rsa_key_file
        self.ssh_connection_timeout = ssh_config.ssh_connection_timeout # in seconds
        self.IP = ipaddress
        self.user = user
        self.port = port

    def establishSSHSession(self):
        if (not self.user) or (not self.IP):
            #self.logger.critical(""))
            return False
        try:
            self.client = paramiko.SSHClient()
            self.client.load_system_host_keys(self.host_key_file)
            self.client.set_missing_host_key_policy(paramiko.client.AutoAddPolicy())
            self.rsa_key = paramiko.RSAKey.from_private_key_file(self.rsa_key_file)
            self.client.connect(self.IP, self.port, self.user,
                                pkey=self.rsa_key,
                                timeout=self.ssh_connection_timeout)
            self.channel = self.client.get_transport().open_session()
            #self.logger.info("")
            return True
        except Exception as err:
            #self.logger.info("")
            self.error = err
            return False


    def killSSHSession(self):
        return self.client.close()

    def executeCommand(self, command='/usr/bin/uptime'):
        if not self.establishSSHSession():
            res, details, exitcode = 'SSH connection failed: {}'.\
                                     format(self.error), None, 2
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
