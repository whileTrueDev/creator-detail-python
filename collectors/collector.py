
from sys import platform
from lib.config_controller import ConfigController
from lib.db_client import DBClient
from lib.api_client import APIClient
from lib.utils import Utils
import pandas as pd
import numpy as np
import copy
import time
PPP = 2
ROWS_PER_ONE_HOUR = 3 * 6


class Collector:
    _config = None
    db_client = None
    api_client = None
    platform = 'twitch'

    def __init__(self):
        self._config = ConfigController()
        self._config.load()

        self.db_client = DBClient(self._config)
        self.db_client.connect(self._config.debug)

        self.api_client = APIClient(self._config)

    def set_platform(self, platform):
        print('{} 플랫폼으로 수행합니다.'.format(platform))
        self.platform = platform

    # 지난 한 달간 실제 배너 게시한 이력이 존재하는 크리에이터 -> 수집대상
    def get_target_data(self):
        return self.db_client.do_target_query(self.platform)

    # 메타데이터 수집
    def get_meta_data(self, creatorList):
        start = time.time()
        print('[{}] meta data 수집 시작'.format(self.platform))
        creators = ''
        impression_data = []
        for (creatorId, platformId, impression_time) in creatorList:
            creators = creators + "'{}'".format(platformId) + ','
            impression_data.append((platformId, impression_time, creatorId))
        creators = creators[:-1]

        # afreeca의 경우, 각각 따로 쿼리 진행 후 merge수행
        if self.platform == 'afreeca':
            meta_df = self.get_afreeca_meta_data(creators)
        else:
            meta_df = self.db_client.do_meta_query(creators)
            meta_df = pd.DataFrame(meta_df, columns=[
                'gameNameKr', 'gameName', 'streamerId', 'streamId', 'viewer', 'gameId', 'startDate', 'hour'])

        if self._config.debug:
            meta_df.to_csv(
                './data/meta_data_{}.csv'.format(self.platform), encoding='utf-8')

        ############ impression time data ##############
        impression_data = pd.DataFrame(impression_data, columns=[
                                       'streamerId', 'impression_time', 'creatorId']).set_index('streamerId')

        # 10분마다 찍히므로 시간당은 6으로 나눠야함.
        impression_data['impression_time'] = np.round(
            impression_data['impression_time'] / 6, 2)

        if self._config.debug:
            impression_data.to_csv(
                './data/impress_{}.csv'.format(self.platform), encoding='utf-8')

        end = time.time()
        print('[{}]  meta data 수집 종료 : {}s'.format(
            self.platform, round(end-start)))
        return meta_df, impression_data

    # 아프리카 메타데이터 수집
    def get_afreeca_meta_data(self, creators):
        # afreeca meta data(broad)
        af_meta_df = self.db_client.do_afreeca_broad_query(creators)
        af_meta_df = pd.DataFrame(af_meta_df, columns=[
            'streamerId', 'streamId', 'viewer', 'gameId', 'startDate', 'hour'])

        # afreeca afeeca category data (game)
        af_category_df = self.db_client.do_afreeca_category_query()
        af_category_df = pd.DataFrame(af_category_df, columns=[
            'gameNameKr', 'gameName', 'gameId']).set_index('gameId')

        merged_data = pd.merge(
            af_category_df,
            af_meta_df,
            left_index=True,
            right_on='gameId',
            how="right"
        )
        return merged_data

    # 디버깅용
    def get_csv_data(self):
        meta_df = pd.read_csv('./data/meta_data_{}.csv'.format(self.platform),
                              encoding='utf-8', index_col=0)
        impress_df = pd.read_csv(
            './data/impress_{}.csv'.format(self.platform), encoding='utf-8', index_col=0)
        return meta_df, impress_df

    # 크리에이터별 실제 방송 비율 계산 [ streamerId | rip | creatorId ]
    def get_rip_data(self, meta_data, impression_data):
        broad_time_data = meta_data.groupby('streamerId').agg({
            'streamerId': 'count'
        })
        broad_time_data.columns = ['broad_time']
        broad_time_data['broad_time'] = np.round(
            broad_time_data['broad_time'].values / 18, 2)

        merged_data = pd.merge(impression_data, broad_time_data,
                               left_index=True,
                               right_index=True,
                               how='left'
                               )
        merged_data['rip'] = np.round(merged_data['impression_time'].values /
                                      merged_data['broad_time'].values, 2)

        # 방송 최소 조건 -> CPS 추가시 제거 필요.
        merged_data = merged_data[merged_data['rip'].values > 0.3]

        merged_data['one'] = 1
        merged_data['rip'] = np.min(merged_data[['rip', 'one']].values, axis=1)

        merged_data['creatorId'] = merged_data['creatorId'].astype(np.str)
        return merged_data[['rip', 'creatorId']]

    # 스트리머 - 방송별 변수 계산 [ streamerId | viewer | peakview | airtime]
    def get_stream_data(self, meta_data):
        stream_data = meta_data.groupby(['streamerId', 'streamId']).agg(
            {'viewer': [np.mean, 'max'], 'streamId': 'count'})

        # column rename
        stream_data.columns = ['viewer', 'peakview', 'airtime']

        grouped_data = stream_data.groupby('streamerId').agg({
            'viewer': np.mean,
            'peakview': 'max',
            'airtime': np.mean,
        })

        # delete outliner -> 조건을 만족하는 방송이 존재하지 않음
        grouped_data = grouped_data[grouped_data['airtime']
                                    >= ROWS_PER_ONE_HOUR]
        # hour count
        grouped_data['airtime'] = grouped_data['airtime'] / ROWS_PER_ONE_HOUR
        grouped_data = np.round(grouped_data).astype('int32')
        return grouped_data

    # 스트리머 - 게임별 비율 및 주요 컨텐츠 계산 [ streamerId | contentsGraphData | content ]
    def get_game_data(self, meta_data):
        stream_data = meta_data.groupby(['streamerId', 'gameId']).agg(
            {'gameId': 'count', 'gameName': 'first', 'gameNameKr': 'first'})
        stream_data.columns = ['count', 'gameName', 'gameNameKr']

        # delete outliner
        stream_data = stream_data[stream_data['count'] >= ROWS_PER_ONE_HOUR]

        game_data = stream_data.groupby(
            'streamerId').apply(Utils.get_game_percent)

        game_data = pd.DataFrame({
            'streamerId': list(game_data.index),
            'contentsGraphData': [x[0] for x in game_data.values],
            'content': [x[1] for x in game_data.values]
        }).set_index('streamerId')
        return game_data

    # 스트리머 - 시간별 비율 계산 [ streamerId | timeGraphData ]
    def get_hour_data(self, meta_data):
        stream_data = meta_data.groupby(['streamerId', 'hour']).agg(
            {'hour': 'count'})
        stream_data.columns = ['count']

        hour_data = stream_data.groupby(
            'streamerId').apply(Utils.get_hour_percent)
        hour_data = pd.DataFrame(hour_data, columns=['timeGraphData'])
        return hour_data

    # 스트리머별 주요 방송 시간대 계산 [ streamerId | openHour ]
    def get_open_hour(self, meta_data):
        base_data = copy.deepcopy(meta_data[['hour', 'streamerId']])
        base_data['hour_name'] = base_data['hour'].apply(Utils.get_hour_name)
        time_data = base_data.groupby(['streamerId', 'hour_name']).agg(
            {'hour_name': 'count'})
        time_data.columns = ['count']
        open_hour_data = time_data.groupby(
            'streamerId').apply(Utils.get_hour_names)
        open_hour_data = pd.DataFrame(open_hour_data, columns=['openHour'])
        return open_hour_data

    # 크리이에이터별 일간 클릭 수 계산 [ creatorId | ctr ]
    def get_click_data(self):
        click_data = self.db_client.do_clicks_query()
        click_df = pd.DataFrame(click_data, columns=[
                                'streamerId', 'ctr']).set_index('streamerId')
        return click_df

    # 플랫폼의 follower갸져오기
    def get_follower_data(self, data_df):
        start = time.time()
        print('[{}] 총 {} 명의 팔로워 수 수집 시작'.format(
            self.platform, len(data_df)))

        follower_list = self.api_client.get_follower(data_df, self.platform)
        follower_df = pd.DataFrame(follower_list, columns=[
                                   'streamerId', 'follower']).set_index('streamerId')
        end = time.time()
        print('[{}] 팔로워 수 수집 종료 : {}s'.format(
            self.platform, round(end-start)))
        return follower_df

    # 전체 데이터 저장
    def save(self, save_data):
        save_records = save_data.to_dict('records')
        self.db_client.do_insert_query(save_records, self.platform)

    # 전체 작업 수행
    def process(self):
        start = time.time()
        print('[{}] 상세정보 수집 시작'.format(self.platform))

        meta_data = None
        impression_data = None
        if not self._config.debug:
            targetList = self.get_target_data()
            meta_data, impression_data = self.get_meta_data(targetList)
        else:
            meta_data, impression_data = self.get_csv_data()

        # 데이터 수집 오류
        if len(meta_data) == 0:
            return

        # [ streamerId | rip | creatorId ]
        rip_data = self.get_rip_data(
            meta_data, impression_data)

        # [ creatorId | ctr ]
        click_data = self.get_click_data()

        # [ streamerId | rip | creatorId | ctr ]
        merged_data = pd.merge(
            rip_data,
            click_data,
            left_on='creatorId',
            right_index=True,
            how="left"
        )

        merge_target_df = [
            # [ streamerId | viewer | peakview | airtime]
            self.get_stream_data(meta_data),
            # [ streamerId | contentsGraphData | content ]
            self.get_game_data(meta_data),
            # [ streamerId | timeGraphData ]
            self.get_hour_data(meta_data),
            # [ streamerId | openHour ]
            self.get_open_hour(meta_data),
            # [ streamerId | follower]
            self.get_follower_data(merged_data)
        ]

        for right_df in merge_target_df:
            merged_data = pd.merge(
                merged_data,
                right_df,
                left_index=True,
                right_index=True,
                how="left"
            )

        merged_data['impression'] = np.round(
            merged_data['airtime'].values * merged_data['viewer'].values * 6 * merged_data['rip'].values).astype('int32')
        merged_data['cost'] = np.round(
            merged_data['viewer'].values * 6 * PPP * merged_data['rip'].values).astype('int32')

        # drop null row
        merged_data.dropna(inplace=True)
        # [ rip | creatorId | ctr | viewer | peakview | airtime | contentsGraphData | content | timeGraphData | openHour | impression | cost | follower ]

        if self._config.debug:
            merged_data.to_csv(
                './data/save_{}.csv'.format(self.platform), encoding='utf-8')
        else:
            if not len(merged_data) == 0:
                self.save(merged_data)
        end = time.time()
        print('[{}] 상세정보 수집 완료 : {}s'.format(
            self.platform, round(end-start)))
