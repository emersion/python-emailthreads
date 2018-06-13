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
	text = text_part.get_payload(decode=True).decode('utf-8')
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

class Text:
	def __init__(self, region, lines=[]):
		self.region = region
		self.lines = lines_as_list(lines)

	def __repr__(self):
		return "[text " + "\n".join(self.lines) + "]"

	def __eq__(self, other):
		return self.region == other.region and self.lines == other.lines

class Quote:
	def __init__(self, region, lines, parent_region=None):
		self.region = region
		self.lines = lines_as_list(lines)
		self.parent_region = parent_region

	def __repr__(self):
		s = "["
		if self.parent_region is not None:
			s += "quote at " + str(self.parent_region[0]) + "-" + str(self.parent_region[1] - 1)
		else:
			s += "unknown quote"

		return s + " " + "\n".join(self.lines) + "]"

	def __eq__(self, other):
		return self.region == other.region and self.lines == other.lines and self.parent_region == other.parent_region

def parse_blocks(msg):
	text = get_text(msg)
	text_lines = text.splitlines()

	blocks = []

	block_start = 0
	block_lines = []
	was_quoted = False
	for (i, line) in enumerate(text_lines):
		line = line.strip()

		line_quoted = line.startswith(">")
		if line_quoted:
			line = line[1:].lstrip()

		if line_quoted != was_quoted and block_lines != []:
			reg = (block_start, i)
			if was_quoted:
				blocks.append(Quote(reg, block_lines))
			else:
				blocks.append(Text(reg, block_lines))
			block_start = i
			block_lines = []

		block_lines.append(line)
		was_quoted = line_quoted

	if block_lines != []:
		reg = (block_start, len(text_lines))
		if was_quoted:
			blocks.append(Quote(reg, block_lines))
		else:
			blocks.append(Text(reg, block_lines))

	return blocks

def match_block_at(ref_block, block, index):
	start = max(0, index - len(block))
	ref_block = list(ref_block[start:index])

	n_lines = 0
	for line in reversed(block):
		if ref_block == []:
			break

		ref_line = ref_block[-1]

		# TODO: match level of quotes
		line = line.lstrip("> ").strip()
		ref_line = ref_line.lstrip("> ").strip()

		if line == ref_line:
			ref_block = ref_block[:-1]
			n_lines += 1
		elif ref_line.endswith(line):
			ref_block[-1] = ref_line[:-len(line)].strip()
		else:
			break

	return n_lines

def find_block(ref_block, block, start=0):
	# TODO: optimize this
	regions = []
	for i in range(start, len(ref_block)):
		match_len = match_block_at(ref_block, block, i)
		# TODO: require to match at least a % of the block
		if match_len > 0:
			regions.append((i - match_len, i))

	return regions

def match_quotes(blocks, in_reply_to):
	in_reply_to_text = get_text(in_reply_to)
	in_reply_to_lines = [l.strip() for l in in_reply_to_text.splitlines()]

	last_quote_index = 0
	for block in blocks:
		block.lines = trim_empty_lines(block.lines)

		if isinstance(block, Quote):
			regions = find_block(in_reply_to_lines, block.lines, last_quote_index)
			regions = sorted(regions, key=lambda reg: reg[1] - reg[0], reverse=True)
			if regions == []:
				# Quote that isn't in the In-Reply-To message
				pass
			else:
				if len(regions) > 1:
					# TODO: ranking
					print("Warning: multiple matches at " + str(regions))
				parent_region = regions[0]
				block.parent_region = parent_region
				last_quote_index = parent_region[0]

	return blocks

def trim_noisy_text(blocks):
	# Trim snips
	# TODO: more of these
	snips = ["...", "…", "[...]", "[snip]", "snip"]
	for block in blocks:
		if isinstance(block, Text) and len(block.lines) == 1 and block.lines[0] in snips:
			blocks.remove(block)

	if len(blocks) >= 2:
		# Trim "On …, … wrote:" headers
		# TODO: support more variations of these
		# TODO: support text comments before this header
		first = blocks[0]
		second = blocks[1]
		if isinstance(first, Text) and first.lines != [] and isinstance(second, Quote):
			if len(first.lines) <= 2 and first.lines[0].startswith("On ") and first.lines[-1].rstrip(" :").endswith(" wrote"):
				blocks = blocks[1:]

	return blocks

def trim_quotes_footer(blocks):
	# TODO: make footers configurable
	# TODO: only trim for the last quotes
	for block in blocks:
		if isinstance(block, Quote):
			# Trim retarded mailing list footers
			try:
				i = block.lines.index("_______________________________________________")
				if i >= 0:
					block.lines = block.lines[:i]
				# TODO: cleanup empty quotes
			except ValueError:
				pass
		else:
			# Trim mailing list scrubbing attachments
			try:
				i = block.lines.index("-------------- next part --------------")
				if i >= 0:
					block.lines = block.lines[:i]
				# TODO: cleanup empty quotes
			except ValueError:
				pass

	return blocks

def quote_to_text(quote):
	lines = ["> " + l for l in quote.lines]
	return Text(quote.region, lines)

def merge_blocks(blocks):
	merged = []

	last_block = None
	for block in blocks:
		merge = False
		if isinstance(block, Text):
			merge = isinstance(last_block, Text)
		elif isinstance(block, Quote):
			if block.parent_region is None:
				# Unknown quote
				merge = isinstance(last_block, Text)
				block = quote_to_text(block)

		if merge:
			last_block.lines += block.lines
		elif block.lines != []:
			merged.append(block)
			last_block = block

	return merged

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

def parse(msg, refs=[]):
	# For some reason Python strips "Re:" prefixes
	subject = flatten_header_field(msg["subject"])

	in_reply_to = get_message_by_id(refs, msg['in-reply-to'])
	if in_reply_to is None or flatten_header_field(in_reply_to["subject"]) != subject:
		text = get_text(msg)
		text_lines = text.splitlines()
		return Thread(text_lines, msg, (0, len(text_lines)))

	blocks = parse_blocks(msg)
	blocks = trim_quotes_footer(blocks)
	blocks = match_quotes(blocks, in_reply_to)
	blocks = trim_noisy_text(blocks)
	# print("\n".join([str(block) for block in blocks]))
	blocks = merge_blocks(blocks)

	thread = parse(in_reply_to, refs)

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
