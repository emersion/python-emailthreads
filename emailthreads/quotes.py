import re
import sys
from email.message import EmailMessage

from .util import *

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
			s += "quote at " + str(self.parent_region[0]) + "-" + str(self.parent_region[1])
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
	end = index + 1
	start = max(0, end - len(block))
	ref_block = list(ref_block[start:end])

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
			j = i - match_len + 1
			regions.append((j, j + match_len))

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
