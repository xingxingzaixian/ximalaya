# encoding: utf-8
import time
import pymongo
from config import MONGODB_HOST, MONGODB_NAME


class MongoDBApi:
    def __init__(self, collection, host=MONGODB_HOST, port=27017):
        client = pymongo.MongoClient(host=host, port=port)
        self.db = client[MONGODB_NAME]
        self.collection = self.db[collection]

    def insert(self, items, many=False, condition=None):
        """

        :param items: 一条或者多条数据
        :param many: 如果为True，表示插入多条数据；如果为False，默认插入一条数据
        :param condition: 如果有条件，表示需要进行去重判断
        :return:
        """
        if condition:
            # 如果查询成功，表示已经存在相同数据，不再新增
            if self.collection.find_one(filter=condition):
                return False

        if many:
            self.collection.insert_many(items)
        else:
            self.collection.insert_one(items)
        return True
