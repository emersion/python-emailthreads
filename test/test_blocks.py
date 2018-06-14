from emailthreads import quotes
import unittest
from email.message import EmailMessage

class ParseBlocksTestCase(unittest.TestCase):
	def _test(self, text, want):
		msg = EmailMessage()
		msg.set_content(text)

		got = quotes.parse_blocks(msg)

		self.assertEqual(got, want)

	def test_only_text(self):
		text = "a\nb\nc"
		want = [quotes.Text((0, 3), text)]
		self._test(text, want)

	def test_only_quote(self):
		text = ">a\n>  b\n> c"
		want = [quotes.Quote((0, 3), "a\nb\nc")]
		self._test(text, want)

	def test_with_quotes(self):
		text = "a\n>b\nc\n> d\n> e\nf"
		want = [
			quotes.Text((0, 1), "a"),
			quotes.Quote((1, 2), "b"),
			quotes.Text((2, 3), "c"),
			quotes.Quote((3, 5), "d\ne"),
			quotes.Text((5, 6), "f"),
		]
		self._test(text, want)

if __name__ == '__main__':
	unittest.main()
