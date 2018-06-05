import mailbox
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

def get_text(msg):
	# TODO: remove "On …, … wrote:"
	# TODO: remove retarded mailing list footers
	text_part = get_text_part(msg)
	return text_part.get_payload(decode=True).decode('utf-8')

def find_sub_list(l, sl):
	indices = []
	for i in range(len(l)):
		# TODO: optimize this
		if l[i:i + len(sl)] == sl:
			indices.append(i)
	return indices

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
	def __init__(self, index, lines=[]):
		self.index = index
		self.lines = lines

	def __repr__(self):
		return "[text " + "\n".join(self.lines) + "]"

class Quote:
	def __init__(self, index, lines, parent_index):
		self.index = index
		self.lines = lines
		self.parent_index = parent_index

	def __repr__(self):
		return "[quote at " + str(self.parent_index) + "-" + str(self.parent_index + len(self.lines)) + " " + "\n".join(self.lines) + "]"

def parse_reply(msg, in_reply_to):
	text = get_text(msg)
	text_lines = text.splitlines()

	in_reply_to_text = get_text(in_reply_to)
	# print(in_reply_to_text)
	in_reply_to_lines = [l.strip() for l in in_reply_to_text.splitlines()]

	blocks = []

	block = []
	quoted_block = []
	last_text = None
	last_quote = None
	for (i, line) in enumerate(text_lines):
		line = line.strip()

		line_quoted = False
		if line.startswith(">"):
			line = line[1:].lstrip()
			line_quoted = True

		if line_quoted:
			if block != []:
				block = trim_empty_lines(block)
				last_text = Text(i, block)
				blocks.append(last_text)
				block = []

			quoted_block.append(line)
		else:
			if quoted_block != []:
				quoted_block = trim_empty_lines(quoted_block)
				indices = find_sub_list(in_reply_to_lines, quoted_block)
				if last_quote is not None:
					indices = list(filter(lambda i: i > last_quote.parent_index, indices))
				if indices == []:
					# Quote that isn't in the In-Reply-To message
					if last_text is None:
						last_text = Text(0) # TODO
						blocks.append(last_text)
					for l in quoted_block:
						last_text.lines.append("> " + l)
				elif len(indices) == 1:
					quote_index = indices[0]
					last_quote = Quote(i, quoted_block, quote_index)
					blocks.append(last_quote)
				else:
					# TODO: ranking
					raise Error("Warning: multiple matches, this isn't supported yet")

				quoted_block = []

			block.append(line)

	return blocks

class Review:
	def __init__(self, lines):
		self.lines = lines
		self.comments = []

	def comment_at(self, index):
		for c in self.comments:
			if c.index is not None and index >= c.index and index < c.index + len(c.lines):
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
				repr_lines.append("[inline comment by " + c.msg["from"] + " at " + c.msg["date"] + "]")
				for l in c.lines:
					repr_lines.append("| " + l)

		for c in standalone_comments:
			repr_lines.append("")
			repr_lines.append("[standalone comment by " + c.msg["from"] + " at " + c.msg["date"] + "]")
			for l in c.lines:
				repr_lines.append("| " + l)

		return "\n".join(repr_lines)

class Comment:
	def __init__(self, msg, lines, index=None, parent=None):
		self.msg = msg
		self.lines = lines
		self.index = index
		self.parent = parent

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

	blocks = parse_reply(msg, in_reply_to)
	# print("\n".join([str(block) for block in blocks]))

	review = parse(in_reply_to, refs)

	last_quote = None
	for block in blocks:
		if isinstance(block, Text):
			c = None
			if last_quote is not None:
				# TODO: find parent comment, if any
				i = last_quote.parent_index + len(last_quote.lines) - 1
				c = Comment(msg, block.lines, i, None)
				last_quote = None
			else:
				c = Comment(msg, block.lines)
			review.comments.append(c)
		elif isinstance(block, Quote):
			last_quote = block

	return review
