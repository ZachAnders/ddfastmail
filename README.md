ddfastmail
=========

ddfastmail is a small script that makes it very easy to automate the modification of
DNS records that are configured through Fastmail's Web Interface. It's primary design
is for letting hosts who are stuck with dynamic IP addresses automatically update
their DNS records whenever their IP address changes.

ddfastmail will log in to fastmail.fm every time it is invoked, but only issues
a POST to the dns configuration page if it detects a record needs updating.

Note: This script only updates existing records, and will not add new ones.

ddfastmail was inspired by a combination of the fantastic open-source ddclient and Fastmail's
unfortunate lack of a DNS api.

Warnings
========

Due to the nature of web scraping, ddfastmail client could break at any time if Fastmail
rolls out an update that drastically alters the layout of the page. For this reason, I
would avoid using ddfastmail for anything where reliability is particularly important.

Requirements
============

ddfastmail was designed for Python 2.x (though shouldn't be hard to port to 3.x) and
requires the python libraries 'requests' and 'beautifulsoup4'.

> pip install requests beautifulsoup4

Configuration
============

Because ddfastmail requires full authentication with the fastmail UI, you must store
a username and password in a configuration file. I suggest making a separate password
under Fastmail's advanced authentication settings.

ddfastmail by default looks for its json configuration file in /etc/ddfastmail.conf.
This can be changed by passing an alternate configuration file on the commandline:

> ./ddfastmail.py myconfig.json

YOUR CONFIGURATION FILE MUST NOT BE GROUP OR WORLD READABLE.
ddfastmail will not read the configuration file if your permissions are too
open. This is because the credentials in the configuration file could also
be used to infiltrate your fastmail account. You should take their
security very seriously.

####Syntax
Domain records in the configuration prefixed with '$' are evaluated as python
statements, and thus can contain variable reference, function calls, or more advanced
expressions.

Included are two example configuration files:

simpleconfig.json
> Simplest possible case. Sets fastmail credentials and a single domain
> to update. $current_ip causes ddfastmail to attempt to eval('current_ip'),
> which resolves to an internal variable set inside ddfastmail.

examplerecordtypes.json:
> Shows both multiple domains and multple records types, all of which
> could potentially be configured separately. Shows both dynamic IPs and
> static IPs. Also includes a TXT record.
