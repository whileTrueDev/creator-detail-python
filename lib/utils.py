import numpy as np
import pandas as pd
import json


class Utils:
    def __init__(self) -> None:
        pass

    # 스트리머별 그룹화된 게임 그룹에서 비율 계산
    @staticmethod
    def get_game_percent(game_group):
        base_df = game_group.reset_index()
        base_df['count'] = base_df['count'].values / \
            np.sum(base_df['count'].values)
        base_df = base_df.sort_values(by='count', ascending=False)
        cumsum = 0
        percents = []
        for row in base_df.itertuples(index=False):
            percent = np.round(row.count, 2)
            if percent < 0.1:
                break
            obj = {
                'gameName': row.gameNameKr if row.gameNameKr else row.gameName,
                'percent': percent
            }
            percents.append(obj)
            cumsum += np.round(row.count, 2)
            if cumsum > 0.8:
                break
        obj = {
            'gameName': '기타',
            'percent': np.round((100 - cumsum * 100) / 100, 2)
        }
        percents.append(obj)
        json_text = json.dumps({
            'data': percents
        }, ensure_ascii=False)

        return json_text, percents[0]['gameName']

    # 스트리머별 그룹화된 시간 그룹에서 비율 계산
    @staticmethod
    def get_hour_percent(hour_group):
        hour_group = hour_group.reset_index().set_index('hour')
        hour_group['count'] = np.round(
            hour_group['count'].values / np.max(hour_group['count'].values), 2)
        hours = []
        stream_hours = list(hour_group.index)
        for time in list(range(6, 24)) + list(range(6)):
            obj = {
                'hours': time,
                'sumtime': 0
            }
            if time in stream_hours:
                obj['sumtime'] = hour_group.loc[time, 'count']
                hours.append(obj)

        json_text = json.dumps({
            'data': hours
        }, ensure_ascii=False)
        return json_text

    # 시간 -> 시간대 변환
    @ staticmethod
    def get_hour_name(time):
        if (time >= 0 and time < 6):
            return '새벽'
        if (time >= 6 and time < 12):
            return '오전'
        if (time >= 12 and time < 18):
            return '오후'
        if (time >= 18 and time < 24):
            return '저녁'

    # 주요 방송 시간대 계산
    @ staticmethod
    def get_hour_names(hour_name_group):
        base_df = hour_name_group.reset_index()
        base_df = base_df.sort_values(by='count', ascending=False)
        hours = list(base_df.itertuples(index=False))
        if len(hours) == 1:
            return hours[0].hour_name

        return '{}, {}'.format(hours[0].hour_name, hours[1].hour_name)
