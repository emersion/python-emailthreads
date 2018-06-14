#!/usr/bin/env python3

import mailbox

from util import *
from threads import *

def get_message_references(msg):
	# TODO: handle spaces in message IDs
	refs_str = flatten_header_field(msg.get("references", ""))
	ref_ids = []
	for ref_id in refs_str.split(" "):
		ref_id = ref_id.strip()
		if ref_id == "":
			continue
		ref_ids.append(ref_id)
	return ref_ids

def print_thread(mbox, msg_id):
	messages_by_id = {}
	for msg in mbox:
		messages_by_id[msg["message-id"]] = msg

	msg = messages_by_id[msg_id]
	ref_ids = get_message_references(msg)
	refs = []
	for ref_id in ref_ids:
		ref = messages_by_id[ref_id]
		if ref is not None:
			refs.append(ref)
		else:
			print("Warning: missing reference " + ref_id)
	thread = parse(msg, refs)
	print(thread)

# TODO: don't hardcode those
# mbox_path = "/home/simon/tmp/wayland-devel/all.mbox"
mbox_path = "/home/simon/tmp/wayland-devel/2018.mbox"
# mbox_path = "/home/simon/tmp/wayland-devel/2018-May.txt"
# msg_id = "<ifhnVLylmcR__mKkQ0yb6e9VU8t-c1zYPYZFbhAUpnxZl8QJio1k4hp4Yv3LqPkhjV1389yNgIDdNwxDGyj5iW1ahatsMoCcEiR75UwnmKY=@emersion.fr>" # Direct reply
# msg_id = "<20180529171002.7a2d3706@eldfell>" # Direct reply
# msg_id = "<1527683902.2337.10.camel@nxp.com>" # Reply of reply
msg_id = "<20180531153835.6ad9e559@eldfell>" # Reply of reply of reply

mbox = mailbox.mbox(mbox_path)
print_thread(mbox, msg_id)
