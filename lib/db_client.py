
from typing import List
from sqlalchemy import create_engine, text
import sqlalchemy


class DBClient:
    _db_url = None
    _engine = None

    def __init__(self, config) -> None:
        db_url = "mysql+pymysql://%s:%s@%s:%s/%s?charset=%s" % (
            config.DB_USER, config.DB_PASSWORD,
            config.DB_HOST, config.DB_PORT,
            config.DB_DATABASE, config.DB_CHARSET
        )
        self._db_url = db_url

    def connect(self, debug) -> None:
        self._engine = create_engine(
            self._db_url, echo=debug, future=True)

    def disconnect(self) -> None:
        self._engine.dispose()

    def do_query(self, query):
        result = None
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(query))
                conn.commit()
            return result.all()
        except:
            return []

    # platform에 따라 분기처리
    def do_target_query(self, platform) -> List:
        # (having impression_time  > 6) 1시간 이상의 배너광고를 수행한 사람 -> CPS가 있기 때문에 해당 조건을 필요하지않다.
        query = '''
        select creatorId, creatorTwitchOriginalId, impression_time
        from
        (
            select creatorId, count(*) as impression_time
            from campaignLog cl
            where date > DATE_SUB(NOW(), INTERVAL 1 MONTH)
            and type = 'CPM'
            group by creatorId
            having impression_time  > 6
        ) as A
        join creatorInfo using (creatorId)
        where creatorTwitchOriginalId IS NOT NULL;
        '''
        if platform == 'afreeca':
            query = '''
            select creatorId, afreecaId, impression_time
            from
            (
                select creatorId, count(*) as impression_time
                from campaignLog cl
                where date > DATE_SUB(NOW(), INTERVAL 1 MONTH)
                and type = 'CPM'
                group by creatorId
                having impression_time  > 6
            ) as A
            join creatorInfo using (creatorId)
            where afreecaId IS NOT NULL;
            '''
        return self.do_query(query)

    # platform에 따라 분기처리
    def do_meta_query(self, params, platform) -> List:
        query = '''
        SELECT gameNameKr, gameName, C.*
        FROM
        (
            SELECT B.streamerId, B.streamId, viewer, A.gameId, startDate, hour(A.time) as hour
            FROM
            (
                SELECT streamId, streamerId, startedAt as startDate
                FROM twitchStream
                WHERE streamerId IN ( {} ) AND startedAt > DATE_SUB(NOW(), INTERVAL 1 MONTH)
            ) AS B
            LEFT JOIN twitchStreamDetail AS A
            USING (streamId)
        ) AS C
        JOIN twitchGame tg
        USING (gameId)
        '''.format(params)
        if platform == 'afreeca':
            query = '''
            SELECT categoryNameKr as categoryNameKr, categoryNameKr as categoryName, C.*
            FROM
            (
                SELECT B.streamerId, B.broadId as streamId, viewCount as viewer, A.broadCategory as categoryId, startDate, hour(A.createdAt) as hour
                FROM
                (
                    SELECT broadId, userId as streamerId, createdAt as startDate
                    FROM AfreecaBroad
                    WHERE userId IN ( {} ) AND createdAt > DATE_SUB(NOW(), INTERVAL 1 MONTH)
                ) AS B
                LEFT JOIN AfreecaBroadDetail AS A
                USING (broadId)
            ) AS C
            JOIN AfreecaCategory ac
            using (categoryId)
            '''.format(params)
        return self.do_query(query)

    def do_clicks_query(self) -> List:
        query = '''
        select creatorId, CEIL(IFNULL(ROUND(avg(counts), 2), 0)) as count
        from
        (
        select count(*) as counts, creatorId
        from tracking t
        where clickedTime > DATE_SUB(NOW(), INTERVAL 1 MONTH)
        group by creatorId, date(clickedTime)
        ) as C
        group by creatorId;
        '''
        return self.do_query(query)

    # platform에 따라 분기처리
    def do_insert_query(self, records, platform) -> None:
        self.disconnect()
        self.connect(False)
        target_table = 'creatorDetail'
        if platform == 'afreeca':
            target_table = 'creatorDetailAfreeca'

        delete_query = '''
        delete from {}
        '''.format(target_table)

        query = '''
        INSERT INTO {}
        (followers, ctr, airtime, viewer, impression, cost, content, openHour, timeGraphData, contentsGraphData, peakview, rip, creatorId)
        VALUES (:follower, :ctr, :airtime, :viewer, :impression, :cost, :content, :openHour, :timeGraphData, :contentsGraphData, :peakview, :rip, :creatorId)
        '''.format(target_table)

        try:
            with self._engine.connect() as conn:
                # 이전 데이터 삭제 작업
                conn.execute(
                    text(delete_query)
                )
                conn.commit()
                conn.execute(
                    text(query),
                    records
                )
                conn.commit()
        except sqlalchemy.exc.StatementError as error:
            print(error)
        self.disconnect()
