import os
from pyctogram.instagram_client import client

if __name__ == '__main__':
    insta_client = client.InstagramClient()
    insta_client.login()
    insta_client.edit_profile(
        "sova_megamozg",
        "sova_anisimus@ruzzy.pro",
        1,
        first_name=None,
        external_url=None,
        biography=None,
        phone_number='+79996391601'
    )


