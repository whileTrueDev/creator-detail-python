import requests
import numpy as np
import time


class APIClient:
    _client_id = None
    _client_secret = None
    _access_token = None

    def __init__(self, config) -> None:
        self._client_id = config.TWITCH_CLIENT_ID
        self._client_secret = config.TWITCH_CLIENT_SECRET

    def get_token(self):
        authorizationUrl = """https://id.twitch.tv/oauth2/token?client_id={}&client_secret={}&grant_type=client_credentials&scope=user:read:email""".format(
            self._client_id, self._client_secret)

        try:
            res = requests.post(authorizationUrl)
            result = res.json()

            self._access_token = result['access_token']
        except:
            print("access token error !")

    def get_follower_one(self, twitchId):
        followers = 0

        # access token 발급
        self.get_token()

        url = """https://api.twitch.tv/helix/users/follows?to_id={}""".format(
            twitchId)
        headers = {
            'Client-ID': "{}".format(self._client_id),
            'Authorization': "Bearer {}".format(self._access_token)
        }
        try:
            res = requests.get(url, headers=headers)
            result = res.json()
            followers = result['total']
        except:
            print('{} call error'.format(twitchId))
        return followers

    def get_follower(self, data_df, platform='twitch'):
        target_list = np.array(data_df.index)
        targets = []
        # 내림 후 계산 -> 30명보다 적을 떄는 하지 않는다.
        if len(target_list) < 30:
            targets = [target_list]
        else:
            turns = int(np.floor(len(target_list) / 30))
            targets = np.split(target_list[:turns * 30], turns)
            targets.append(target_list[turns * 30:])

        follower_list = []
        for target in targets:
            for twitchId in target:
                if platform == 'twitch':
                    follower = self.get_follower_one(twitchId)
                else:
                    follower = self.get_follower_one_afreeca(twitchId)
                follower_list.append((twitchId, follower))
            time.sleep(50)

        return follower_list

    def get_follower_one_afreeca(self, afreecaId):
        followers = 0
        url = """https://bjapi.afreecatv.com/api/{}/station""".format(
            afreecaId)
        headers = {
            'User-Agent': 'Mozilla/5.0'
        }
        try:
            res = requests.get(url, headers=headers)
            result = res.json()
            followers = result['station']['upd']['fan_cnt']
        except:
            print('call error')
        return followers
