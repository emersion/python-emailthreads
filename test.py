#!/usr/bin/env python3

import mailbox

from emailreview import *

def get_message_references(msg):
	# TODO: handle empty references
	# TODO: handle spaces in message IDs
	refs_str = flatten_header_field(msg.get("references", ""))
	ref_ids = refs_str.split(" ")
	return [ref_id.strip() for ref_id in ref_ids]

def print_review(mbox, msg_id):
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
	review = parse(msg, refs)
	print(review)

# TODO: don't hardcode those
# mbox_path = "/home/simon/tmp/wayland-devel/all.mbox"
mbox_path = "/home/simon/tmp/wayland-devel/2018.mbox"
# mbox_path = "/home/simon/tmp/wayland-devel/2018-May.txt"
# msg_id = "<ifhnVLylmcR__mKkQ0yb6e9VU8t-c1zYPYZFbhAUpnxZl8QJio1k4hp4Yv3LqPkhjV1389yNgIDdNwxDGyj5iW1ahatsMoCcEiR75UwnmKY=@emersion.fr>"
msg_id = "<20180529171002.7a2d3706@eldfell>"
# msg_id = "<20180531153835.6ad9e559@eldfell>"

mbox = mailbox.mbox(mbox_path)
print_review(mbox, msg_id)
