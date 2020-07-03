# emailthreads

[![builds.sr.ht status](https://builds.sr.ht/~emersion/python-emailthreads.svg)](https://builds.sr.ht/~emersion/python-emailthreads?)

Python library to parse and format email threads. Give it a list of emails that
are part of the same thread and it'll build a tree of responses to the original
message.

```python
import emailthreads
import mailbox

mbox = mailbox.mbox("/path/to/mbox/thread")
thread = emailthreads.parse(mbox)
print(thread)
```

## Tests

To run the tests, execute this command:

    python3 -m pytest test

Given some raw messages, you can parse a thread from the CLI like so:

    python3 -m emailthreads *.eml

## License

MIT
