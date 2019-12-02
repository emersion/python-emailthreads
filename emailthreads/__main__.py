import sys
import emailthreads
from email import message_from_file

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print("usage: python3 -m emailthreads <files...>", file=sys.stderr)
		sys.exit(1)

	files = sys.argv[1:]

	messages = []
	for path in files:
		with open(path) as f:
			msg = message_from_file(f)
			messages.append(msg)

	thread = emailthreads.parse(messages)

	print(str(thread))
