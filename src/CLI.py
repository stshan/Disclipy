from .DiscordClient import DiscordClient
from .observer import Observer
from getpass import getpass

from prompt_toolkit import prompt, print_formatted_text, HTML
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name
from .Validators import (
    JoinableGuildListValidator,
    JoinableChannelListValidator
)
from xml.sax.saxutils import escape
import click


class CLI(Observer):
    def __init__(self, config_file):
        Observer.__init__(self)
        self.client = DiscordClient(self, config_file)
        click.clear()

        self.current_guild = None
        self.current_channel = None
        self.channel_open = False

    def login(self):
        # Check config file for setup status
        if self.client.config['CREDENTIALS']['Token'] == 'placeholder_token':
            email = prompt('Email: ')
            password = prompt('Password: ', is_password=True)

            if not self.client.config['CREDENTIALS']['AutoLogin']:
                auto_login = prompt('Automatically login in the future? y/n: ')
                while auto_login not in ['y', 'n']:
                    auto_login = prompt('Invalid selection. Please select y/n')

                self.client.login_with_email_password(email, password)

                if auto_login:
                    self.client.config['CREDENTIALS']['AutoLogin'] = 'True'
                    self.client.config['CREDENTIALS']['Token'] = self.client.session_token
                else:
                    self.client.config['CREDENTIALS']['Autologin'] = 'False'

                with open(self.client.config_file, 'w') as configfile:
                    self.client.config.write(configfile)
        else:
            self.update('login_in_progress')
            self.client.run(self.client.config['CREDENTIALS']['Token'], bot=False)

    def open_channel(self):
        click.clear()
        self.channel_open = True
        self.client.emit('open_channel', self.current_channel)

    def display_guilds(self):
        guilds = ''
        for i, guild in enumerate(self.client.guilds):
            guilds += '{0}: {1}\n'.format(i, guild.name)
        click.echo_via_pager(guilds)
        click.echo('Select a server by entering the corresponding server number')
        self.select_guild()

    def select_guild(self):
        selection = int(
            prompt('>', validator=JoinableGuildListValidator(len(self.client.guilds))))
        self.current_guild = self.client.guilds[int(selection)]
        click.clear()
        click.secho(
            'Connected to {}'.format(
                self.current_guild.name),
            fg='black',
            bg='white')
        self.select_channel()

    def select_channel(self):
        if self.current_guild:
            channels = ''
            text_channels = self.current_guild.text_channels

            for channel in text_channels:
                channels += '#' + channel.name + '\n'

            click.echo_via_pager(channels)
            click.echo('Select a channel by entering the corresponding #channel-name')

            completer = WordCompleter(['#' + t.name for t in text_channels])

            selection = prompt('>',
                               validator=JoinableChannelListValidator(text_channels),
                               completer=completer)

            for channel in text_channels:
                if selection[1:] == channel.name:
                    self.current_channel = channel

            self.open_channel()

    def update(self, action: str, data=None):
        """Prints information passed by DiscordClient
        """
        # login actions
        if action == 'login_in_progress':
            click.echo('Logging in...')
        elif action == 'login_successful':
            click.clear()
            click.secho('You are logged in.', fg='black', bg='white')
            self.display_guilds()
        elif action == 'login_incorrect_email_format':
            click.secho('Not a well formed email address.', fg='red', bold=True)
            self.login()
        elif action == 'login_incorrect_password':
            click.secho('Password is incorrect.', fg='red', bold=True)
            self.login()
        elif action == 'login_captcha_required':
            click.secho(
                'Captcha required.\n' +
                'Please login through the Discord web client first.\n' +
                'https://discordapp.com/login', fg='red', bold=True)
            self.login()

        # message actions
        elif action == 'message':
            msg = data
            if self.current_channel:
                if self.current_channel.id == msg.channel.id and self.channel_open:
                    print_formatted_text(HTML(
                        '<_ fg="%s">%s</_>> %s' % (
                            str(msg.author.color),
                            msg.author.display_name,
                            escape(msg.content)
                        )))
