import emailthreads
import os
import unittest
from email.message import EmailMessage
from email import message_from_file

class ParseTestCase(unittest.TestCase):
	def _normalize(self, output):
		output = output.strip()
		lines = output.split("\n")
		lines = [l.strip() for l in lines]
		return "\n".join(lines)

	def _open_file(self, name):
		dir_path = os.path.dirname(os.path.realpath(__file__))
		return open(dir_path + "/data/" + name)

	def _load_msg_from_file(self, name):
		f = self._open_file(name)
		msg = message_from_file(f)
		f.close()
		return msg

	def _read_file(self, name):
		f = self._open_file(name)
		contents = f.read().strip()
		f.close()
		return self._normalize(contents)

	def test_with_scissor(self):
		patch = self._load_msg_from_file("scissor/patch.eml")
		reply = self._load_msg_from_file("scissor/reply.eml")

		thread = emailthreads.parse([patch, reply])

		got = self._normalize(str(thread))
		want = self._read_file("scissor/output.txt")

		self.assertEqual(got, want)

	def test_with_multiple_replies(self):
		patch = self._load_msg_from_file("multiple-replies/patch.eml")
		reply1 = self._load_msg_from_file("multiple-replies/reply1.eml")
		reply2 = self._load_msg_from_file("multiple-replies/reply2.eml")
		reply3 = self._load_msg_from_file("multiple-replies/reply3.eml")

		thread = emailthreads.parse([patch, reply1, reply2, reply3])

		got = self._normalize(str(thread))
		want = self._read_file("multiple-replies/output3.txt")

		self.assertEqual(got, want)

if __name__ == '__main__':
	unittest.main()
