import re
import sys
from email.message import EmailMessage

def get_message_by_id(msgs, msg_id):
	# TODO: handle weird brackets stuff
	for msg in msgs:
		if msg["message-id"] == msg_id:
			return msg
	return None

def strip_prefix(s, prefix):
	if s.startswith(prefix):
		s = s[len(prefix):]
	return s

def flatten_header_field(value):
	value = value.strip()
	# TODO: more of these
	while value.startswith("Re:"):
		value = strip_prefix(value, "Re:").strip()
	lines = value.splitlines()
	lines = [l.strip() for l in lines]
	return " ".join(lines)

def get_text_part(msg):
	for part in msg.walk():
		if part.get_content_type() == "text/plain":
			return part
	return None

def normalize_whitespace(text):
	# TODO: more of these
	# No-break space
	return text.replace('\xa0', ' ')

def get_text(msg):
	text_part = get_text_part(msg)
	text = text_part.get_payload(decode=True).decode('utf-8', 'replace')
	text = normalize_whitespace(text)
	return text

def lines_as_list(lines):
	if isinstance(lines, list):
		return lines
	elif isinstance(lines, str):
		return lines.split("\n")
	else:
		return list(lines)
