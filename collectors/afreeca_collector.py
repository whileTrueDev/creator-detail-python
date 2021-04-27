from collectors.collector import Collector
import pandas as pd
import numpy as np

# 상속버전, 테스트


class AfreecaCollector(Collector):
    def __init__(self) -> None:
        super().__init__()
        self.platform = 'afreeca'

    # overriding -> 기존 트위치에서 아프리카로
    def get_target_data(self):
        return self.db_client.do_target_query_afreeca()

    # overriding, 메타데이터 수집
    def get_meta_data(self, creatorList):
        creators = ''
        impression_data = []
        for (creatorId, afreecaId, impression_time) in creatorList:
            creators = creators + "'{}'".format(afreecaId) + ','
            impression_data.append((afreecaId, impression_time, creatorId))
        creators = creators[:-1]

        meta_df = self.db_client.do_meta_query_afreeca(creators)
        meta_df = pd.DataFrame(meta_df, columns=[
            'gameNameKr', 'gameName', 'streamerId', 'streamId', 'viewer', 'gameId', 'startDate', 'hour'])

        if self._config.debug:
            meta_df.to_csv('./data/meta_data.csv', encoding='utf-8')

        ############ impression time data ##############
        impression_data = pd.DataFrame(impression_data, columns=[
                                       'streamerId', 'impression_time', 'creatorId']).set_index('streamerId')

        # 10분마다 찍히므로 시간당은 6으로 나눠야함.
        impression_data['impression_time'] = np.round(
            impression_data['impression_time'] / 6, 2)

        if self._config.debug:
            impression_data.to_csv(
                './data/impress_afreeca.csv', encoding='utf-8')

        return meta_df, impression_data

    # 전체 데이터 저장
    def save(self, save_data):
        save_records = save_data.to_dict('records')
        self.db_client.do_insert_query_afreeca(save_records)
