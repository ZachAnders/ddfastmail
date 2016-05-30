#!/usr/bin/env python

"""
Simple little script that allows one to automatically update DNS records through Fastmail's GUI.
I could not find an official API, so this relies on beautiful soup to naviagate through fastmail's
HTML pages.
"""

import requests, re, os, sys
import json
from bs4 import BeautifulSoup

FASTMAIL_URL = "https://www.fastmail.com"

class FastmailUpdater():
	""" The fastmail updater manages the state necessary to navigate Fastmail's
		Web interface. By maintaining an internal session, you can perform multiple
		DNS updates, but only need to perform a login once. """
	def __init__(self):
		self.sess = requests.session()
		self.logged_in = False
		self.user_id = None

	def login(self, username, password):
		""" Attempts to login to fastmail with the given username and password.
			If we fail to login to fastmail, this method will throw a RuntimeError """
		response = self.sess.get(FASTMAIL_URL)

		session_key = re.search('<input value="([0-9a-g]*)" name="sessionKey"', response.content, re.IGNORECASE).group(1)
		form = {"sessionKey": session_key,
				"dologin": 1,
				"hasPushState": 1,
				"interface": 'text',
				'username': username,
				'password': password,
				'screenSize': 'desktop',
				}

		response = self.sess.post(FASTMAIL_URL, form, headers={'referer':FASTMAIL_URL})
		result = re.search("u=([0-9a-g]*)&", response.content)
		if result is None:
			raise ValueError("Could not find user_id! (Wrong username/password?)")
		else:
			self.user_id = result.group(1)
			self.logged_in = True
	
	def parse_static_fields(self, page):
		""" Parses out all of the constant fields present in the page that are
			hidden input fields with fixed values. We don't change these, but the
			server-side probably validates whether or not they are present/valid.
			Most of them are probably related to CSRF, authentication, or other security issues.
			"""
		inputs = []
		for input_field in page.body.form.find_all('input'):
			if 'value' in input_field.attrs and 'name' in input_field.attrs:
				inputs.append([input_field.attrs['name'], input_field.attrs['value']])
				
		f_to_extract = ("MLS", 'SCD-DM', "MSS", "MSignalFeedback", "MSessionKey", "MSessionKeySeed", "FCD-DM")
		static_inputs = [inp for inp in inputs if "CKS" in inp[0] or inp[0] in f_to_extract]
		results = {'FCD-HasCustomDNS': '1'}
		for inp in static_inputs:
			results[inp[0]] = inp[1]
		return results

	def parse_domain(self, row):
		""" Parses out the domain name from the given DNS record's row.
			Returns ('domains', '<domainname>') """

		# The domain name is split up in the first three columns
		# Column one is the subdomain, column two is just a period,
		# and three is the TLD itself.
		# Ex. 'mail' | '.' | 'example.com'
		text = [col.text for col in row[0:3]]
		if text[0] == '':
			# There is no subdomain, so skip the subdomain column and period
			# I.E. ('', '.', 'example.com') -> 'example.com'
			text = text[2]
		else:
			text = "".join(text)
		return "domain", text

	def parse_ttl(self, row):
		""" Parses out the ttl value of the given DNS record's row.
			This is a little sketchy, since fastmail configures TTL in the UI with a combo box.
			Returns ('ttl', ('<inputname>', '<ttlvalue>')) """
		column_index = 3
		select_box = row[column_index].find('select')
		for select_option in select_box.find_all('option'):
			if 'selected' in select_option.attrs:
				return 'ttl', (select_box.attrs['name'], select_option.attrs['value'])
		raise NameError("Unable to find TTL option!")
		
	def parse_rec_type(self, row):
		""" Parses out the record type of the given DNS record's row. (A, MX, NS, TXT, etc.)
			Returns ('type', '<recordtype>') """
		column_index = 4
		return "type", row[column_index].text
	
	def parse_rec_data(self, row):
		""" Parses out the actual data value contained in the given DNS record's row.
			The contents vary depending on row type. (IP addresses for A records, strings for CNAMEs, etc.)
			Returns ('data', ('<inputname>', '<recordvalue')) """
		column_index = 5
		column = row[column_index]
		return 'data', (column.input.attrs['name'], column.input.attrs['value'])
		
	def parse_active(self, row):
		""" Parses out the active checkbox from the given DNS record's row.
			Returns ('active', ('<inputname>', 'on'|'off')) """
		column_index = 6
		column = row[column_index]
		return 'active', (column.input.attrs['name'], 'on' if column.input.attrs['checked'] == 'checked' else 'off')

	def get_dns_records(self, page):
		""" Gets a list of all the DNS records in the DNS config pages' table. """
		table = page.body.form.find(class_="contentTable")
		rows = table.find_all("tr")
		# The first row is just column headers, the last is for adding new records. We skip both.
		rows = rows[1:-1]
		rows = [row.find_all('td') for row in rows] # Break up individual columns
		records = []
		for row in rows:
			record = {}
			record.update([self.parse_domain(row)])
			record.update([self.parse_ttl(row)])
			record.update([self.parse_rec_type(row)])
			record.update([self.parse_rec_data(row)])
			record.update([self.parse_active(row)])
			records.append(record)
		return records

	def dns_update(self, node_key, new_value, types_to_change=('A',)):
		""" Checks to see if the records of type 'types_to_change' and domain 'node_key' need
			to be updated. If so, it submits fastmail's configuration page. Only performs
			an update if it detects a change. """
		if not self.logged_in:
			raise RuntimeError("Please log in first")
		dns_page = FASTMAIL_URL + "/html/?MLS=ASE-*&u=%s&MSignal=CD-*U-1" % self.user_id
		response = self.sess.get(dns_page)

		page = BeautifulSoup(response.content)
		static_inps = self.parse_static_fields(page)
		records = self.get_dns_records(page)

		form = {}
		form_needs_update = False
		form.update(static_inps) #These are hidden inputs at the top of the page. Probably for CSRF or something

		for record in records: 
			form.update([record['ttl']])
			form.update([record['active']])
			data_key, original_data_val = record['data']
			if record['domain'] == node_key and record['type'] in types_to_change:
				if str(original_data_val).strip() != str(new_value).strip():
					print("Update: The '%s' record for domain '%s' needs updating" % (record['type'], record['domain']))
					print("Old value: '%s', New Value: '%s'" % (original_data_val, new_value))
					form[data_key] = str(new_value)
					form_needs_update = True
			else:
				form[data_key] = original_data_val

		if form_needs_update:
			print("One or more records need updating. Submitting request...")
			response = self.sess.post(FASTMAIL_URL + "/html/?u=%s" % self.user_id, form)
			if not response.ok:
				print("Failed to submit request: %s" % response.text)
				response.raise_for_status() #Should raise an HTTPError with error code/msg
		else:
			print("Found no changes in records %s for domain '%s'." % (types_to_change, node_key))

def get_ip():
	""" Simple helper method that retrieves the current hosts outward facing IP address.
		Uses the free service at ifconfig.me """
	ip = requests.get("http://whatismyip.akamai.com").text
	return ip.strip()

if __name__ == "__main__":
	if len(sys.argv) > 1:
		print("Using configuration file: %s" % sys.argv[1])
		conf = sys.argv[1]
	else:
		conf = "/etc/ddfastmail.conf"
	if not os.path.exists(conf):
		raise RuntimeError("File does not exist! %s" % conf)
	if os.stat(conf).st_mode & 044 > 0:
		raise RuntimeError("Config permissions too open! Please use mode 400 or 600 (go-rwx).")
	with open(conf, 'r') as conf_in:
		config = json.load(conf_in)

	updater = FastmailUpdater()
	updater.login(config['username'], config['password'])

	#configuration constants defined here:
	current_ip = get_ip()

	#pylint: disable=W0123
	for domain in config['domains']:
		dns_records = config['domains'][domain]
		if type(dns_records) == dict:
			# Multiple record types for single domain stored in a dict
			for record_type in dns_records:
				if dns_records[record_type].startswith('$'):
					dns_records[record_type] = eval(dns_records[record_type][1:])
				updater.dns_update(domain, dns_records[record_type], types_to_change=record_type)
		elif type(dns_records) in (str, unicode):
			# Default record type for a domain ('A' record), stored in a single string
			if dns_records.startswith('$'):
				dns_records = eval(dns_records[1:])
			updater.dns_update(domain, dns_records)

		
