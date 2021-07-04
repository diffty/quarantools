import os
import sys
import json
import datetime
import asyncio
import threading
import time
import traceback

from flask import Flask, jsonify, Response, request
import requests

import nextup
import utip
from twitch import Twitch

from config import load_config
from queue import Queue


NOTIFICATION_QUEUES = []


app = Flask(__name__)
twitch = Twitch("jhmtkftnyi4lopji4wwam6ywvw7d0o")


def main():
    while True:
        try:
            print("<i> Refreshing donations")
            db = utip.DonationsDb.get().get_db()

            new_donations = utip.DonationsDb.get().get_new_entries()

            #new_donations.append(list(db.values())[-1])

            if new_donations:
                for d in new_donations:
                    if d["type"] in ["direct", "recurring"]:
                        event_payload = {
                            "type": "utip_donation",
                            "content": {
                                "username": d["username"],
                                "amount": d["amount"],
                                "message": d["message"],
                            },
                        }

                        print("<i> Sending notification for the donation : %s" % event_payload)

                        for q in NOTIFICATION_QUEUES:
                            q.put(json.dumps(event_payload))

                        if len(NOTIFICATION_QUEUES) > 0:
                            print("<i> Flushing new entries")
                            utip.DonationsDb.get().flush_new_entries()

        except Exception as e:
            print("<!!> Donation refresh failed : %s\n" % e)
            tb = sys.exc_info()[2]
            traceback.print_tb(tb)

        sys.stdout.flush()
        sys.stderr.flush()

        time.sleep(60)


t = threading.Thread(target=main)
t.start()


@app.route('/last_donations')
def last_donations():
    config = load_config()

    db = utip.DonationsDb.get().get_db()

    sorted_list = sorted(db.values(), key=lambda u: u["datetime"]["date"])
    filtered_list = filter(lambda u: u["amount"] is not None, sorted_list)
    
    filtered_data = list(map(lambda u: {
        "type": u["type"],
        "username": u["username"],
        "datetime": u["datetime"],
        "amount": u["amount"],
        "message": u["message"],
    }, filtered_list))

    response = jsonify(filtered_data)
    response.headers.add('Access-Control-Allow-Origin', '*')

    sys.stdout.flush()
    
    return response


def event_stream(q):
    try:
        while True:
            message = q.get(True)
            print("Sending {}".format(message))
            yield "data: {}\n\n".format(message)
    finally:
        NOTIFICATION_QUEUES.remove(q)
        print("user quit")


@app.route('/notifications_stream')
def notifications_stream():
    print("User Subscribed (count: %s)" % len(NOTIFICATION_QUEUES))

    q = Queue()
    NOTIFICATION_QUEUES.append(q)

    response = Response(event_stream(q), mimetype="text/event-stream")
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/next_up')
def next_up():
    config = load_config()

    current_event, next_event = nextup.main(config["google_calendar_id"])

    def _format_event_dict(event):
        if event:
            return {
                "startDateTime": event["start"]["dateTime"],
                "endDateTime": event["end"]["dateTime"],
                "summary": event["summary"],
            }
        else:
            return None

    response_dict = {
        "current": _format_event_dict(current_event),
        "next": _format_event_dict(next_event),
    }

    response = jsonify(response_dict)
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


@app.route('/subscribe/twitch/<string:topic_name>', methods=['GET'])
def subscribe(topic_name):
    if topic_name == "follows":
        twitch.subscribe(
            "http://freddyclement.com:1312/notification/follows",
            "https://api.twitch.tv/helix/users/follows?first=1&to_id=27497503"
        )

    return ""


@app.route('/notification/<string:topic_name>', methods=['GET', 'POST'])
def notification(topic_name):
    if request.method == "POST":
        if topic_name == "follows":
            data = request.get_json()
            for notif_info in data["data"]:
                print("Nouveau follow de %s !" % notif_info["from_name"])
                
                event_payload = {
                    "type": "twitch_follow",
                    "content": notif_info,
                }

                for q in NOTIFICATION_QUEUES:
                    q.put(json.dumps(event_payload))

    if request.method == "GET":
        if topic_name == "follows":
            challenge_token = request.args.get('hub.challenge', '')

            if challenge_token:
                headers = {
                    "Content-Type": "text/plain",
                    "Client-ID": twitch.client_id,
                }

                response = requests.post(
                    "https://api.twitch.tv/helix/webhooks/hub",
                    data=challenge_token,
                    headers=headers,
                )

                return challenge_token

    return ""


@app.route('/jill/say')
def jill_say():
    if request.method == "GET":
        msg = request.args.get("msg", None)
        if msg:
            event_payload = {
                "type": "jill_say",
                "content": {
                    "msg": msg
                },
            }

            for q in NOTIFICATION_QUEUES:
                q.put(json.dumps(event_payload))

    return ""
