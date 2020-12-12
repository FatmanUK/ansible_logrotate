#!/usr/bin/python

'''
Ansible callback plugin to run logrotate on the ansible.log file
'''

from __future__ import (absolute_import, division, print_function)
from time import sleep
from subprocess import Popen, PIPE
from os import fork, _exit, path, mkdir, getcwd
import sys
from ansible.plugins.callback import CallbackBase

DOCUMENTATION = '''
  callback: logrotate
  callback_type: aggregate
  requirements:
    - whitelist in configuration
  short_description: Run logrotate
  version_added: "2.0"
  description:
    - Logrotate the log every run so it's more convenient for upload.
  options:
    confdir:
      description: Configuration directory
      ini:
      - section: callback_logrotate
        key: confdir
      env:
        - name: ANSIBLE_CALLBACK_LOGROTATE_CONFDIR
      default: "$HOME/.lr"
    logdir:
      description: Log directory
      ini:
      - section: callback_logrotate
        key: logdir
      env:
        - name: ANSIBLE_CALLBACK_LOGROTATE_LOGDIR
      default: "$HOME/ansible_logs"
'''

# By the way, the file is prefixed with 'zzz_' to ensure it runs last.
# This is possibly not foolproof.

class CallbackModule(CallbackBase):
    """
    This callback module rotates ansible.log using the logrotate program.
    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'logrotate'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super().__init__()
        print('started logrotate plugin')

    def v2_playbook_on_stats(self, stats):
        super().v2_playbook_on_stats(stats)
        # detach from Ansible and run logrotate after a delay
        try:
            pid = fork()
            if pid > 0:
                return
        except OSError:
            print('Error: Unable to fork')
            sys.exit(1)
        sleep(0.5)
        # special exit to avoid multiple calls to atexit
        print('')
        self.check_config_installed()
        self.run_logrotate()
        _exit(0)

    def check_config_installed(self):
        '''Check the config exists and is correct'''
        print('Checking logrotate config...')
        logdir = path.expandvars(self._plugin_options['logdir'])
        confdir = path.expandvars(self._plugin_options['confdir'])
        print('logdir = %s' % logdir)
        print('confdir = %s' % confdir)
        # check directories exist and have conf file in
        if not path.exists(logdir):
            mkdir(logdir)
        else:
            if not path.isdir(logdir) and not path.islink(logdir):
                _exit(1)
        if not path.exists(confdir):
            mkdir(confdir)
        else:
            if not path.isdir(confdir) and not path.islink(confdir):
                _exit(1)
        # read list of files from ~/.lr/logrotate.conf, first lines before '{',
        # only add if not present
        files = []
        # *** TO DO ***
        if not '%s/ansible.log' % getcwd() in files:
            files += ['%s/ansible.log' % getcwd()]
        # output conf file - %s format is Unix timestamp
        lines = files
        lines += [
            '{',
            '	rotate 1000',
            '	missingok',
            '	notifempty',
            '	dateext',
            '	dateformat -%s',
            '	compress',
            '	olddir %s' % logdir,
            '	size 1',
            '}',
        ]
        conffile = open('%s/logrotate.conf' % confdir, 'w')
        for line in lines:
            conffile.write(str(line) + '\n')
        conffile.close()

    def run_logrotate(self):
        '''Run logrotate'''
        logdir = path.expandvars(self._plugin_options['logdir'])
        confdir = path.expandvars(self._plugin_options['confdir'])
        print('Rotating log file...')
        print('logdir = %s' % logdir)
        print('confdir = %s' % confdir)
        cmd = [
            '/usr/bin/logrotate',
            '-s',
            '%s/logrotate.state' % confdir,
            '%s/logrotate.conf' % confdir,
        ]
        print('Running %s...' % cmd)
        pipe = Popen(cmd, cwd='/', stdout=PIPE, stderr=PIPE)
        for line in pipe.stdout:
            print(line)
