import mailbox
import re
import sys

def get_message_by_id(msgs, msg_id):
	# TODO: handle weird brackets stuff
	for msg in msgs:
		if msg["message-id"] == msg_id:
			return msg
	return None

def flatten_header_field(value):
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

def match_block(ref_block, block):
	ref_block = list(ref_block)
	ref_block_len = len(ref_block)

	for line in block:
		if len(ref_block) == 0:
			return -1

		# TODO: match level of quotes
		# TODO: don't strip again when splitting line
		line = line.lstrip("> ").lstrip()
		ref_block[0] = ref_block[0].lstrip("> ").lstrip()

		if line == ref_block[0]:
			ref_block = ref_block[1:]
		elif ref_block[0].startswith(line):
			ref_block[0] = ref_block[0][len(line):].strip()
		else:
			return -1

	return ref_block_len - len(ref_block)

def find_block(ref_block, block):
	# TODO: optimize this
	regions = []
	for i in range(len(ref_block)):
		match_len = match_block(ref_block[i:], block)
		if match_len >= 0:
			regions.append((i, i + match_len))
	return regions

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

class Text:
	def __init__(self, region, lines=[]):
		self.region = region
		self.lines = lines

	def __repr__(self):
		return "[text " + "\n".join(self.lines) + "]"

class Quote:
	def __init__(self, region, lines, parent_region=None):
		self.region = region
		self.lines = lines
		self.parent_region = parent_region

	def __repr__(self):
		s = "["
		if self.parent_region is not None:
			s += "quote at " + str(self.parent_region[0]) + "-" + str(self.parent_region[1] - 1)
		else:
			s += "unknown quote"

		return s + " " + "\n".join(self.lines) + "]"

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

	return blocks

def match_quotes(blocks, in_reply_to):
	in_reply_to_text = get_text(in_reply_to)
	in_reply_to_lines = [l.strip() for l in in_reply_to_text.splitlines()]

	last_quote_index = -1
	for block in blocks:
		block.lines = trim_empty_lines(block.lines)

		if isinstance(block, Quote):
			regions = find_block(in_reply_to_lines, block.lines)
			regions = list(filter(lambda reg: reg[0] > last_quote_index, regions))
			if len(regions) > 1:
				# TODO: ranking
				print("Warning: multiple matches at " + str(regions))
				regions = [regions[0]]
			if regions == []:
				# Quote that isn't in the In-Reply-To message
				pass
			elif len(regions) == 1:
				parent_region = regions[0]
				block.parent_region = parent_region
				last_quote_index = parent_region[0]

	return blocks

def trim_noisy_text(blocks):
	if len(blocks) < 2:
		return blocks

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
	# Trim retarded mailing list footers
	# TODO: make this configurable
	# TODO: only trim for the last quotes
	for block in blocks:
		if not isinstance(block, Quote):
			continue

		try:
			i = block.lines.index("_______________________________________________")
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

class Review:
	def __init__(self, lines):
		self.lines = lines
		self.comments = []

	def comment_at(self, msg, index):
		for c in self.comments:
			if c.source_msg == msg and index >= c.source_region[0] and index < c.source_region[1]:
				return c
		return None

	def __repr__(self):
		comments_by_line = {}
		standalone_comments = []
		for c in self.comments:
			if c.index is not None:
				if c.index not in comments_by_line:
					comments_by_line[c.index] = [c]
				else:
					comments_by_line[c.index].append(c)
			else:
				standalone_comments.append(c)

		repr_lines = []
		for (i, line) in enumerate(self.lines):
			repr_lines.append(line)

			for c in comments_by_line.get(i, []):
				repr_lines.append("[inline comment by " + c.source_msg["from"] + " at " + c.source_msg["date"] + "]")
				for l in c.lines:
					repr_lines.append("| " + l)

		for c in standalone_comments:
			repr_lines.append("")
			repr_lines.append("[standalone comment by " + c.source_msg["from"] + " at " + c.source_msg["date"] + "]")
			for l in c.lines:
				repr_lines.append("| " + l)

		return "\n".join(repr_lines)

class Comment:
	def __init__(self, source_msg, source_region, lines, index=None, parent=None):
		self.source_msg = source_msg
		self.source_region = source_region
		self.lines = lines
		self.index = index
		self.parent = parent
		self.children = []

		if parent is not None:
			parent.children.append(self)

	def __repr__(self):
		return "[comment at " + str(self.index) + " " + "\n".join(self.lines) + "]"

def parse(msg, refs=[]):
	# For some reason Python strips "Re:" prefixes
	subject = flatten_header_field(msg["subject"])

	in_reply_to = get_message_by_id(refs, msg['in-reply-to'])
	if in_reply_to is None or flatten_header_field(in_reply_to["subject"]) != subject:
		text = get_text(msg)
		text_lines = text.splitlines()
		return Review(text_lines)

	blocks = parse_blocks(msg)
	blocks = trim_quotes_footer(blocks)
	blocks = match_quotes(blocks, in_reply_to)
	blocks = trim_noisy_text(blocks)
	# print("\n".join([str(block) for block in blocks]))
	print("")
	for block in blocks:
		if isinstance(block, Quote):
			print(block.region, block.parent_region, block.lines[0])
		else:
			print(block.region, block.lines[0])
	blocks = merge_blocks(blocks)

	review = parse(in_reply_to, refs)
	is_first_reply = review.comments == []

	last_quote = None
	for block in blocks:
		if isinstance(block, Text):
			c = None
			if last_quote is not None:
				assert(last_quote.parent_region is not None)
				i = last_quote.parent_region[1] - 1
				if is_first_reply:
					c = Comment(msg, block.region, block.lines, i)
				else:
					# TODO: split original comment?
					parent = review.comment_at(in_reply_to, i)
					if parent is not None:
						c = Comment(msg, block.region, block.lines, parent.index, parent)
					else:
						# TODO: include previous quote, if any
						c = Comment(msg, block.region, block.lines)
				last_quote = None
			else:
				# TODO: include previous quote, if any
				c = Comment(msg, block.region, block.lines)
			review.comments.append(c)
		elif isinstance(block, Quote):
			last_quote = block

	return review
