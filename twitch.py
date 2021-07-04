import requests


class Twitch:
    def __init__(self, client_id):
        self.client_id = client_id

    def subscribe(self, callback, topic):
        data = {
            "hub.callback": callback,
            "hub.mode": "subscribe",
            "hub.topic": topic,
            "hub.lease_seconds": 60*60*24*7,
        }

        headers = {
            'Client-ID': self.client_id
        }

        response = requests.post(
            "https://api.twitch.tv/helix/webhooks/hub",
            data=data,
            headers=headers,
        )

    def confirm_subscription(self, challenge_token):
        pass

    def receive_notification(self, topic_name, data):
        pass
