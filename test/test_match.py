from emailthreads import quotes
import os
import unittest
from email.message import EmailMessage

class MatchBlocksTestCase(unittest.TestCase):
	def _read_file(self, name):
		dir_path = os.path.dirname(os.path.realpath(__file__))
		with open(dir_path + "/data/" + name, 'r') as f:
			return f.read().strip()

	def _read_file_as_message(self, name):
		msg = EmailMessage()
		msg.set_content(self._read_file(name))
		return msg

	def test_simple(self):
		msg = self._read_file_as_message("simple/msg.txt")
		reply = self._read_file_as_message("simple/reply.txt")
		want = self._read_file("simple/blocks.txt")

		blocks = quotes.parse_blocks(reply)
		blocks = quotes.match_quotes(blocks, msg)
		got = "\n".join([str(block) for block in blocks])

		self.assertEqual(got, want)

if __name__ == '__main__':
	unittest.main()
