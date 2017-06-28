#!/usr/bin/env python3
"""
docker xmpp notify - get an xmpp message when there is an update
for your docker containers.
"""
# (C) 2017 Magnus Walbeck
# mw@mwalbeck.org

import docker
import requests
import sleekxmpp

jid = ""
jpassword = ""
jto = ""

# First part of the xmpp message
message_header = "Docker container updates:"
# Variable for the docker container that have an update available
message_content = ""

base_url = "https://hub.docker.com/v2/repositories"

client = docker.from_env()

class SendMsg(sleekxmpp.ClientXMPP):
    
    def __init__(self, jid, password, recipient, message):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.recipient = recipient
        self.msg = message
        
        self.add_event_handler("session_start", self.start, threaded=True)

    def start(self, event):
        self.send_message(mto=self.recipient, mbody=self.msg, mtype='chat')

        self.disconnect(wait=True)
        

def get_url(base_url, image_name):
    name_split = split_image_name(image_name)
    return "{}/{}/{}/tags/{}".format(base_url, name_split[0], name_split[1], name_split[2])


def split_image_name(image_name):
    return [get_user(image_name), get_repository(image_name), get_tag(image_name)]


def get_user(image_name):
    if '/' in image_name:
        return image_name.split('/')[0]
    
    return 'library'


def get_repository(image_name):
    if '/' in image_name:
        image_name = image_name.split('/')[1]

    if ':' in image_name:
        image_name = image_name.split(':')[0]

    return image_name


def get_tag(image_name):
    if ':' in image_name:
        return image_name.split(':')[1]
    
    return 'latest'


def parse_date(date):
    parsed_date = date.split('T')
    return parsed_date[0]


def get_local_updated(image_name):
    image = client.images.get(image_name)
    return parse_date(image.attrs['Created'])


def get_remote_updated(url):
    r = requests.get(url)
    return parse_date(r.json()['last_updated'])


for container in client.containers.list():
    container_image = container.attrs['Config']['Image']

    url = get_url(base_url, container_image)

    local_updated = get_local_updated(container_image)
    remote_updated = get_remote_updated(url)

    if remote_updated > local_updated:
        message_content += "\n" + container.attrs['Name'][1:] + " - " + remote_updated

if message_content:
    message = message_header + message_content
    xmpp = SendMsg(jid, jpassword, jto, message)

    if xmpp.connect():
        xmpp.process(block=True)