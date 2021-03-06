# -*- coding: utf-8 -*-
#
# This file is part of the FMN project.
# Copyright (C) 2017 Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA
"""Unit tests for the :mod:`fmn.formatters` module."""

import json

import fedmsg.meta
import mock
import requests

from . import Base
from fmn import formatters
from fmn.lib import models


class ShortenTests(Base):
    """Tests for :func:`fmn.formatters.shorten`."""

    def test_no_link(self):
        """Assert an empty string is returned when no link is provided."""
        self.assertEqual('', formatters.shorten(None))

    @mock.patch('fmn.formatters.requests.get')
    def test_failed_request(self, mock_get):
        """Assert a failed request results in the original link."""
        mock_get.side_effect = requests.exceptions.RequestException()

        self.assertEqual('original link', formatters.shorten('original link'))

    @mock.patch('fmn.formatters.requests.get')
    def test_success(self, mock_get):
        mock_get.return_value.text = '\n http://so.short/abc \n'
        shortened_link = formatters.shorten('http://www.example.com/')

        self.assertEqual('http://so.short/abc', shortened_link)


class IrcTests(Base):
    """Tests for :func:`fmn.formatters.irc`."""
    def setUp(self):
        super(IrcTests, self).setUp()
        fedmsg.meta.make_processors(**self.config)
        self.message = {
            u'username': u'apache',
            u'i': 1,
            u'timestamp': 1478281861,
            u'msg_id': u'2016-c2184569-f9c4-4c52-affd-79e28848d70f',
            u'crypto': u'x509',
            u'topic': u'org.fedoraproject.prod.buildsys.task.state.change',
            u'msg': {
                u'info': {
                    u'children': [],
                    u'parent': None,
                    u'channel_id': 1,
                    u'start_time': u'2016-11-04 17:51:01.254871',
                    u'request': [
                        u'../packages/eclipse/4.5.0/1.fc26/src/eclipse-4.5.0-1.fc26.src.rpm',
                        u'f26',
                        {u'scratch': True, u'arch_override': u'x86_64'}
                    ],
                    u'state': 1,
                    u'awaited': None,
                    u'method': u'build',
                    u'priority': 50,
                    u'completion_time': None,
                    u'waiting': None,
                    u'create_time': u'2016-11-04 17:50:57.825631',
                    u'owner': 3199,
                    u'host_id': 82,
                    u'label': None,
                    u'arch': u'noarch',
                    u'id': 16289846
                },
                u'old': u'FREE',
                u'attribute': u'state',
                u'method': u'build',
                u'instance': u'primary',
                u'owner': u'koschei',
                u'new': u'OPEN',
                u'srpm': u'eclipse-4.5.0-1.fc26.src.rpm',
                u'id': 16289846
            }
        }
        self.recipient = {
            "triggered_by_links": False,
            "markup_messages": False,
            "user": "jcline.id.fedoraproject.org",
            "filter_name": "firehose",
            "filter_oneshot": True,
            "filter_id": 7,
            "shorten_links": False,
            "verbose": True,
        }

    def test_confirmation(self):
        """Assert the IRC confirmation message is formatted as expected."""
        confirmation = models.Confirmation(
            secret='a'*32,
            detail_value='jeremy@jcline.org',
            openid='jcline.id.fedoraproject.org',
            context_name='email',
        )
        expected = u"""
jcline.id.fedoraproject.org has requested that notifications be sent to this nick
* To accept, visit this address:
  http://localhost:5000/confirm/accept/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
* Or, to reject you can visit this address:
  http://localhost:5000/confirm/reject/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
Alternatively, you can ignore this.  This is an automated message, please
email notifications@fedoraproject.org if you have any concerns/issues/abuse.
I am run by Fedora Infrastructure.  Type 'help' for more information.
"""

        message = formatters.irc_confirmation(confirmation)

        self.assertEqual(expected.strip(), message)

    @mock.patch('fmn.formatters.arrow.get')
    def test_format_unmarked(self, mock_arrow):
        mock_arrow.return_value.humanize.return_value = '2 months ago'
        expected_message = (
            u'koschei\'s scratch build of eclipse-4.5.0-1.fc26.src.rpm for f26 started 2 months'
            u' ago http://koji.fedoraproject.org/koji/taskinfo?taskID=16289846'
        )
        formatted_message = formatters.irc(self.message, self.recipient)
        self.assertEqual(expected_message, formatted_message)


class SseTests(Base):

    def setUp(self):
        super(SseTests, self).setUp()
        fedmsg.meta.make_processors(**self.config)

    def test_format_message_conglomerated(self):
        """Assert conglomerated messages are formatted"""
        message = {
            u'subtitle': u'relrod pushed commits to ghc and 487 other packages',
            u'link': u'http://example.com/',
            u'icon': u'https://that-git-logo',
            u'secondary_icon': u'https://that-relrod-avatar',
            u'start_time': 0,
            u'end_time': 100,
            u'human_time': u'5 minutes ago',
            u'usernames': [u'relrod'],
            u'packages': [u'ghc', u'nethack'],
            u'topics': [u'org.fedoraproject.prod.git.receive'],
            u'categories': [u'git'],
            u'msg_ids': {
                u'2014-abcde': {
                    u'subtitle': u'relrod pushed some commits to ghc',
                    u'title': u'git.receive',
                    u'link': u'http://...',
                    u'icon': u'http://...',
                },
                u'2014-bcdef': {
                    u'subtitle': u'relrod pushed some commits to nethack',
                    u'title': u'git.receive',
                    u'link': u'http://...',
                    u'icon': u'http://...',
                },
            },
        }
        recipient = {
            "triggered_by_links": True,
            "markup_messages": True,
            "user": "jcline.id.fedoraproject.org",
            "filter_name": "firehose",
            "filter_oneshot": True,
            "filter_id": 7,
            "shorten_links": False,
            "verbose": True,
        }

        formatted_message = formatters.sse(message, recipient)
        formatted_message = json.loads(formatted_message)
        for key in ('dom_id', 'date_time', 'icon', 'link', 'markup', 'secondary_icon'):
            self.assertTrue(key in formatted_message)

    def test_format_message_raw(self):
        """Assert raw messages are formatted"""
        message = {
            u'username': u'apache',
            u'i': 1,
            u'timestamp': 1478281861,
            u'msg_id': u'2016-c2184569-f9c4-4c52-affd-79e28848d70f',
            u'crypto': u'x509',
            u'topic': u'org.fedoraproject.prod.buildsys.task.state.change',
            u'msg': {
                u'info': {
                    u'children': [],
                    u'parent': None,
                    u'channel_id': 1,
                    u'start_time': u'2016-11-04 17:51:01.254871',
                    u'request': [
                        u'../packages/eclipse/4.5.0/1.fc26/src/eclipse-4.5.0-1.fc26.src.rpm',
                        u'f26',
                        {u'scratch': True, u'arch_override': u'x86_64'}
                    ],
                    u'state': 1,
                    u'awaited': None,
                    u'method': u'build',
                    u'priority': 50,
                    u'completion_time': None,
                    u'waiting': None,
                    u'create_time': u'2016-11-04 17:50:57.825631',
                    u'owner': 3199,
                    u'host_id': 82,
                    u'label': None,
                    u'arch': u'noarch',
                    u'id': 16289846
                },
                u'old': u'FREE',
                u'attribute': u'state',
                u'method': u'build',
                u'instance': u'primary',
                u'owner': u'koschei',
                u'new': u'OPEN',
                u'srpm': u'eclipse-4.5.0-1.fc26.src.rpm',
                u'id': 16289846
            }
        }
        recipient = {
            "triggered_by_links": True,
            "markup_messages": True,
            "user": "jcline.id.fedoraproject.org",
            "filter_name": "firehose",
            "filter_oneshot": True,
            "filter_id": 7,
            "shorten_links": False,
            "verbose": True,
        }

        formatted_message = formatters.sse(message, recipient)
        formatted_message = json.loads(formatted_message)
        for key in ('dom_id', 'date_time', 'icon', 'link', 'markup', 'secondary_icon'):
            self.assertTrue(key in formatted_message)


class EmailTests(Base):

    def test_base_email(self):
        """Assert the basic email has the auto-generation headers."""
        message = formatters._base_email()

        self.assertEqual(message['Auto-Submitted'], 'auto-generated')
        self.assertEqual(message['Precedence'], 'Bulk')

    def test_confirmation(self):
        """Assert a :class:`models.Confirmation` is formatted to an email."""
        confirmation = models.Confirmation(
            secret='a'*32,
            detail_value='jeremy@jcline.org',
            openid='jcline.id.fedoraproject.org',
            context_name='email',
        )
        expected = """Precedence: Bulk
Auto-Submitted: auto-generated
To: jeremy@jcline.org
From: notifications@fedoraproject.org
Subject: Confirm notification email

jcline.id.fedoraproject.org has requested that notifications be sent to this email address
* To accept, visit this address:
  http://localhost:5000/confirm/accept/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
* Or, to reject you can visit this address:
  http://localhost:5000/confirm/reject/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
Alternatively, you can ignore this.  This is an automated message, please
email notifications@fedoraproject.org if you have any concerns/issues/abuse."""

        message = formatters.email_confirmation(confirmation)

        self.assertEqual(expected, message)

    def test_email(self):
        """Assert a well-formed email is returned from a basic message."""
        expected = (
            "Precedence: Bulk\n"
            "Auto-Submitted: auto-generated\n"
            "To: jeremy@jcline.org\n"
            "From: notifications@fedoraproject.org\n"
            "X-Fedmsg-Topic: org.fedoraproject.dev.fmn.filter.update\n"
            "X-Fedmsg-Category: fmn\n"
            "X-Fedmsg-Username: jcline\n"
            "Subject: jcline updated the rules on a fmn email filter\n"
            "MIME-Version: 1.0\n"
            "Content-Type: text/plain; charset=\"utf-8\"\n"
            "Content-Transfer-Encoding: base64\n\n"
            "amNsaW5lIHVwZGF0ZWQgdGhlIHJ1bGVzIG9uIGEgZm1uIGVtYWlsIGZpbHRlcgoJaHR0cHM6Ly9h\n"
            "cHBzLmZlZG9yYXByb2plY3Qub3JnL25vdGlmaWNhdGlvbnMv\n"
        )
        message = {
            "msg": {
                "changed": "rules",
                "context": "email",
                "openid": "jcline.id.fedoraproject.org"
            },
            "msg_id": "2017-6aa71d5b-fbe4-49e7-afdd-afcf0d22802b",
            "timestamp": 1507310730,
            "topic": "org.fedoraproject.dev.fmn.filter.update",
            "username": "vagrant"
        }
        recipient = {
            "email address": "jeremy@jcline.org",
            "filter_id": 11,
            "filter_name": "test",
            "filter_oneshot": False,
            "markup_messages": False,
            "shorten_links": False,
            "triggered_by_links": False,
            "user": "jcline.id.fedoraproject.org",
            "verbose": True,
        }

        actual = formatters.email(message, recipient)
        self.assertEqual(expected, actual)
