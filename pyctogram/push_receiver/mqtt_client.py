import logging
import asyncio
from fbns.fbns_mqtt import FBNSMQTTClient

from ig_notify_data import InstagramNotification

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

STOP = asyncio.Event()

MQTT_HOST = 'mqtt-mini.facebook.com'
MQTT_PORT = 443
MQTT_SSL = True
MQTT_KEEPALIVE = 900


class IgMQTT:
    def __init__(self, web_client):
        self.mqtt_client = FBNSMQTTClient()
        self.web_client = web_client

        self.mqtt_client.on_fbns_auth = self.on_fbns_auth
        self.mqtt_client.on_fbns_token = self.on_fbns_token
        self.mqtt_client.on_fbns_message = self.on_fbns_message

    def on_fbns_auth(self, auth):
        pass

    def on_fbns_token(self, token):
        self.web_client.login()
        self.web_client.register_push(token)

    def on_fbns_message(self, push):
        if push.payload:
            notification = InstagramNotification(push.payload)
            if notification.collapseKey == 'comment':
                print(notification.message)
            elif notification.collapseKey == 'direct_v2_message':
                print(notification.it)

    async def listener(self):
        await self.mqtt_client.connect(MQTT_HOST, MQTT_PORT, ssl=MQTT_SSL, keepalive=MQTT_KEEPALIVE)
        await STOP.wait()
        await self.mqtt_client.disconnect()
