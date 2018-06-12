import emailreview
import unittest
from email.message import EmailMessage

class ParseBlocksTestCase(unittest.TestCase):
	def _test(self, text, want):
		msg = EmailMessage()
		msg.set_content(text)

		got = emailreview.parse_blocks(msg)

		self.assertEqual(got, want)

	def test_only_text(self):
		text = "a\nb\nc"
		want = [emailreview.Text((0, 3), text)]
		self._test(text, want)

	def test_only_quote(self):
		text = ">a\n>  b\n> c"
		want = [emailreview.Quote((0, 3), "a\nb\nc")]
		self._test(text, want)

	def test_with_quotes(self):
		text = "a\n>b\nc\n> d\n> e\nf"
		want = [
			emailreview.Text((0, 1), "a"),
			emailreview.Quote((1, 2), "b"),
			emailreview.Text((2, 3), "c"),
			emailreview.Quote((3, 5), "d\ne"),
			emailreview.Text((5, 6), "f"),
		]
		self._test(text, want)

if __name__ == '__main__':
	unittest.main()
