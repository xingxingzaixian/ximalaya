# encoding: utf-8
"""
@version: 1.0
@author: 
@file: ximalay
@time: 2019-05-14 23:06
"""
import time
from json import JSONDecodeError
import requests
from db import MongoDBApi
from utils import now_time
from apscheduler.schedulers.blocking import BlockingScheduler


class GiftList:
    def __init__(self, url):
        self.session = requests.session()
        self.session.verify = False
        self.session.headers = {
            'host': 'liveroom.ximalaya.com'
        }
        self._url = url

    @property
    def url(self):
        if self._url and self._url.find('?ts') == -1:
            return '{}?ts={}'.format(self._url, now_time())
        return None

    def get_rank(self):
        try:
            response = self.session.get(self.url)
            rank_items = response.json().get('data').get('rankItems')
            for info in rank_items:
                item = dict()
                item['contribution'] = info.get('contribution')  # 喜爱值
                item['liveStatus'] = info.get('liveStatus')  # 直播状态 9:正在直播  1:不在直播
                item['nickname'] = info.get('nickname')
                item['rank'] = info.get('rank')
                item['uid'] = info.get('uid')
                item['roomId'] = info.get('roomId')
                yield item
        except JSONDecodeError as e:
            print(e)

    # 获取当前正在直播的直播间信息
    def get_online_player(self, uid, room_id):
        try:
            headers = {'host': 'live.ximalaya.com'}
            url = 'http://183.6.210.144/lamia/v10/live/room?id={}&roomId={}&timeToPreventCaching={}'
            response = self.session.get(url.format(uid, room_id, now_time()), headers=headers)
            info = response.json().get('data')

            item = dict()
            # 获取粉丝团信息
            item['fans_name'] = info.get('fansClubVo').get('clubName')
            item['fans_count'] = info.get('fansClubVo').get('count')

            # 直播间信息
            item['name'] = info.get('recordInfo').get('name')
            start_time = int(info.get('recordInfo').get('actualStartAt') / 1000)
            item['start_time'] = time.strftime('%Y-%m-%d %H:%M:%S',
                                               time.localtime(start_time)) if start_time else ''
            end_time = int(info.get('recordInfo').get('actualStopAt') / 1000)
            item['end_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)) if end_time else ''

            # 分组ID
            item['category_id'] = info.get('recordInfo').get('categoryId')
            # 在线人数
            item['online_count'] = info.get('recordInfo').get('onlineCount')
            # 参与人数
            item['play_count'] = info.get('recordInfo').get('playCount')
            # 用户头像
            item['avatar'] = info.get('userInfo').get('largeAvatar')
            return item
        except JSONDecodeError as e:
            print(e)
        except requests.exceptions.ReadTimeout as e:
            print(e)
        return None

    def save_liveroom_info(self, item):
        now_day = time.strftime('%Y-%m-%d', time.localtime())
        item['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        MongoDBApi('online_player_{}'.format(now_day)).insert(item)

    def save_gift_info(self, item, gift_type):
        collection = 'gift_rank'

        item['type'] = gift_type.lower()
        item['create_time'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        MongoDBApi(collection).insert(item)

    def parse_gift(self):
        raise


class GiftHour(GiftList):
    def __init__(self):
        url = 'http://114.80.139.232/gift-rank/v1/gift/rank/anchor/hour'
        # url = 'http://113.215.21.128/gift-rank/v1/gift/rank/anchor/hour'
        super().__init__(url)

    def parse_gift(self):
        for item in self.get_rank():
            self.save_gift_info(item, 'hour')
            info = self.get_online_player(item['uid'], item['roomId'])
            self.save_liveroom_info(info)


class GiftDay(GiftList):
    def __init__(self):
        url = 'http://114.80.170.77/gift-rank/v1/gift/rank/anchor/daily'
        super().__init__(url)

    def parse_gift(self):
        for item in self.get_rank():
            self.save_gift_info(item, 'day')
            info = self.get_online_player(item['uid'], item['roomId'])
            self.save_liveroom_info(info)


class GiftWeek(GiftList):
    def __init__(self):
        url = 'http://114.80.139.232/gift-rank/v1/gift/rank/anchor/week'
        super().__init__(url)

    def parse_gift(self):
        for item in self.get_rank():
            self.save_gift_info(item, 'week')
            info = self.get_online_player(item['uid'], item['roomId'])
            self.save_liveroom_info(info)


def spider_gift(class_name):
    gift = class_name()
    gift.parse_gift()


def start_apscheduler():
    scheduler = BlockingScheduler()

    scheduler.add_job(spider_gift, trigger='cron', args=(GiftHour,), minute=58)

    scheduler.add_job(spider_gift, trigger='cron', args=(GiftDay,), hour=23, minute=58)

    scheduler.add_job(spider_gift, trigger='cron', args=(GiftWeek,), day_of_week='sun', hour=23, minute=58)

    try:
        scheduler.start()
    except Exception as _:
        scheduler.shutdown()


if __name__ == '__main__':
    start_apscheduler()
