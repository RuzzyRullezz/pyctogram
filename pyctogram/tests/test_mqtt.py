import asyncio

from pyctogram.instagram_client import client
from pyctogram.push_receiver.mqtt_client import IgMQTT

if __name__ == '__main__':
    insta_client = client.InstagramClient()
    ig_mqtt = IgMQTT(insta_client)
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(ig_mqtt.listener())
    except asyncio.CancelledError:
        pass
