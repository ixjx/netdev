"""Subclass specific to Cisco ASA."""

import re

from ..logger import logger
from ..cisco_like import CiscoLikeDevice


class CiscoAsa(CiscoLikeDevice):
    """Subclass specific to Cisco ASA."""

    def __init__(self, host=u'', username=u'', password=u'', secret=u'', port=22, device_type=u'', known_hosts=None,
                 local_addr=None, client_keys=None, passphrase=None, loop=None):
        super().__init__(host=host, username=username, password=password, secret=secret, port=port,
                         device_type=device_type, known_hosts=known_hosts, local_addr=local_addr,
                         client_keys=client_keys, passphrase=passphrase, loop=loop)
        self._current_context = 'system'
        self._multiple_mode = False

    @property
    def current_context(self):
        """ Returning current context for ASA"""
        return self._current_context

    @property
    def multiple_mode(self):
        """ Returning Bool True if ASA in multiple mode"""
        return self._multiple_mode

    async def connect(self):
        """
        Async Connection method

        Usual using 4 functions:
            establish_connection() for connecting to device
            set_base_prompt() for finding and setting device prompt
            enable() for getting privilege exec mode
            disable_paging() for non interact output in commands
        """
        logger.info("Host {}: Connecting to device".format(self._host))
        await self._establish_connection()
        await self._set_base_prompt()
        await self._enable()
        await self._disable_paging()
        await self._check_multiple_mode()
        logger.info("Host {}: Connected to device".format(self._host))

    async def send_command(self, command_string, strip_prompt=True, strip_command=True):
        """
        If the ASA is in multi-context mode, then the base_prompt needs to be
        updated after each context change.
        """
        output = await super(CiscoAsa, self).send_command(command_string=command_string, strip_prompt=strip_prompt,
                                                          strip_command=strip_command)
        if "changet" in command_string:
            await self._set_base_prompt()
        return output

    async def _set_base_prompt(self):
        """
        Setting three important vars for ASA
            base_prompt - textual prompt in CLI (usually hostname)
            base_pattern - regexp for finding the end of command. IT's platform specific parameter
            context - current context for ASA. If ASA in single mode, context = system

        For ASA devices base_pattern is "prompt(\/\w+)?(\(.*?\))?[#|>]
        """
        logger.info("Host {}: Setting base prompt".format(self._host))
        prompt = await self._find_prompt()
        context = 'system'
        # Cut off prompt from "prompt/context"
        if '/' in prompt:
            prompt, context = prompt[:-1].split('/')
        else:
            prompt = prompt[:-1]
        self._base_prompt = prompt
        self._current_context = context
        delimeter1 = self._get_default_command('delimeter1')
        delimeter2 = self._get_default_command('delimeter2')
        self._base_pattern = r"{}.*(\/\w+)?(\(.*?\))?[{}|{}]".format(re.escape(self._base_prompt[:12]),
                                                                     re.escape(delimeter1), re.escape(delimeter2))
        logger.debug("Host {}: Base Prompt: {}".format(self._host, self._base_prompt))
        logger.debug("Host {}: Base Pattern: {}".format(self._host, self._base_pattern))
        logger.debug("Host {}: Current Context: {}".format(self._host, self._current_context))
        return self._base_prompt

    async def _check_multiple_mode(self):
        """
        Check mode multiple. If mode is multiple we adding info about contexts
        """
        logger.info("Host {}:Checking multiple mode".format(self._host))
        out = await self.send_command('show mode')
        if 'multiple' in out:
            self._multiple_mode = True

        logger.debug("Host {}: Multiple mode: {}".format(self._host, self._multiple_mode))

    def _get_default_command(self, command):
        """
        Returning default commands for device

        :param command: command for returning
        :return: real command for this network device
        """
        # @formatter:off
        command_mapper = {
            'delimeter1': '>',
            'delimeter2': '#',
            'pattern': r"{}.*?(\(.*?\))?[{}|{}]",
            'disable_paging': 'terminal pager 0',
            'priv_enter': 'enable',
            'priv_exit': 'disable',
            'config_enter': 'conf t',
            'config_exit': 'end',
            'config_check': ')#',
            'check_config_mode': ')#',
        }
        # @formatter:on
        return command_mapper[command]
