import re
import sys
import email
from email.message import EmailMessage

from .util import *
from .quotes import *

def canonical_msg_id(msg_id):
	if msg_id == None:
		return None
	msg_id = str(msg_id).strip()
	if msg_id == "":
		return None
	# TODO: handle weird brackets stuff
	return msg_id

def get_message_by_id(msgs, msg_id):
	msg_id = canonical_msg_id(msg_id)
	if msg_id == None:
		return None
	for msg in msgs:
		if canonical_msg_id(msg["message-id"]) == msg_id:
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

def trim_empty_lines(block):
	start = 0
	for (i, l) in enumerate(block):
		if l != "":
			break
		start = i + 1
	block = block[start:]

	end = len(block)
	for (i, l) in enumerate(reversed(block)):
		if l != "":
			break
		end = len(block) - i - 1
	block = block[:end]

	return block

def lines_as_list(lines):
	if isinstance(lines, list):
		return lines
	elif isinstance(lines, str):
		return lines.split("\n")
	else:
		return list(lines)

def quote_str(s):
	lines = s.split("\n")
	lines = ["| " + l for l in lines]
	return "\n".join(lines)

class Thread:
	def __init__(self, lines, source_msg, source_region, index=None):
		self.source_msg = source_msg
		self.source_region = source_region
		self.lines = lines_as_list(lines)
		self.index = index
		self.children = []

	def at(self, msg, index):
		if self.source_msg == msg and index >= self.source_region[0] and index < self.source_region[1]:
			return self

		for c in self.children:
			cc = c.at(msg, index)
			if cc is not None:
				return cc
		return None

	def __repr__(self):
		children_by_line = {}
		standalone_children = []
		for c in self.children:
			if c.index is not None and c.index < len(self.lines):
				if c.index not in children_by_line:
					children_by_line[c.index] = [c]
				else:
					children_by_line[c.index].append(c)
			else:
				standalone_children.append(c)

		repr_lines = []
		for (i, line) in enumerate(self.lines):
			repr_lines.append(line)

			for c in children_by_line.get(i, []):
				repr_lines.append("[inline thread by " + c.source_msg["from"] + " at " + c.source_msg["date"] + "]")
				s = quote_str(str(c))
				repr_lines.append(s)

		for c in standalone_children:
			repr_lines.append("[standalone thread by " + c.source_msg["from"] + " at " + c.source_msg["date"] + "]")
			s = quote_str(str(c))
			repr_lines.append(s)

		return "\n".join(repr_lines)

def build_message_tree(messages):
	heads = []
	replies = []

	for msg in messages:
		in_reply_to = get_message_by_id(messages, msg['in-reply-to'])
		if in_reply_to is None:
			heads.append(msg)
		else:
			replies.append((msg, in_reply_to))

	if len(heads) != 1:
		raise Exception("expected exactly one head message, got " + str(len(heads)))
	head = heads[0]

	# TODO: topological sort
	replies = sorted(replies, key=lambda reply: email.utils.parsedate(reply[0]['date']))

	return (head, replies)

def parse_reply(msg, in_reply_to, thread):
	subject = flatten_header_field(msg["subject"])

	blocks = parse_blocks(msg)
	blocks = trim_quotes_footer(blocks)
	blocks = match_quotes(blocks, in_reply_to)
	blocks = trim_noisy_text(blocks)
	# print("\n".join([str(block) for block in blocks]))
	blocks = merge_blocks(blocks)

	last_quote = None
	for block in blocks:
		if isinstance(block, Text):
			c = None
			if last_quote is not None:
				assert(last_quote.parent_region is not None)
				i = last_quote.parent_region[1] - 1
				parent = thread.at(in_reply_to, i)
				if parent is not None:
					c = Thread(block.lines, msg, block.region, i - parent.source_region[0])
					parent.children.append(c)
				else:
					# TODO: include previous quote, if any
					c = Thread(block.lines, msg, block.region)
					thread.children.append(c)
				last_quote = None
			else:
				# TODO: include previous quote, if any
				c = Thread(block.lines, msg, block.region)
				thread.children.append(c)
		elif isinstance(block, Quote):
			last_quote = block

	return thread

def parse(messages):
	(head, replies) = build_message_tree(messages)

	text = get_text(head)
	text_lines = text.splitlines()
	thread = Thread(text_lines, head, (0, len(text_lines)))

	for (msg, in_reply_to) in replies:
		parse_reply(msg, in_reply_to, thread)

	return thread
