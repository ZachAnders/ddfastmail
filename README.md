ddfastmail
=========

ddfastmail is a small script that makes it very easy to automate the modification of
DNS records on fastmail. It's primary design is for letting hosts who are stuck with
dynamic IP addresses automatically update their DNS records whenever their IP address
changes.

ddfastmail will login to fastmail.fm every time it is invoked, but will only issue
a POST to the dns configuration page if it detects a record needs updating.

Note: This script only updates existing records, and will not add new ones.

Configuration
============

Because ddfastmail requires full authentication with the fastmail UI, you must store
a username and password in a configuration file. I suggest making a separate password
under Fastmail's advanced authentication settings.

ddfastmail by default looks for its json configuration file in /etc/ddfastmail.conf.
This can be changed by passing an alternate configuration file on the commandline:
	./ddfastmail.py myconfig.json

YOUR CONFIGURATION FILE MUST NOT BE GROUP OR WORLD READABLE.
ddfastmail will not read the configuration file if your permissions are too
open. This is because the credentials in the configuration file could also
be used to infiltrate your fastmail account. You should take their
security very seriously.

####Syntax:
Domain records in the configuration prefixed with '$' are evaluated as python
statements, and thus can contain variable reference, function calls, or more advanced
expressions.

Included are two example configuration files
simpleconfig.json
> Simplest possible case. Sets fastmail credentials and a single domain
> to update. $current_ip causes ddfastmail to attempt to eval('current_ip'),
> which resolves to an internal variable set inside ddfastmail.

examplerecordtypes.json
> Shows both multiple domains and multple records types, all of which
> could potentially be configured separately. Shows both dynamic IPs and
> static IPs. Also include a TXT record.
