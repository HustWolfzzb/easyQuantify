"""
pyMongDB操作：
    #>>> from pymongo import MongoClient
    # 默认主机与端口
    #>>> client = MongoClient()
    # 指定主机与端口
    #>>> client = MongoClient('localhost', 27017)
    # MongoDBURI格式
    #>>> client = MongoClient('mongodb://localhost:27017/')

    获取数据库
        db = client['test-database']
    获取集合
        collection = db['test-collection']
    查看数据库中所有集合
        db.collection_names(include_system_collections=False)
    对一个集合中插入一个文档（行） post:{}
        post_id = collection.insert_one(post).inserted_id
    对一个集合中插入许多文档（行） data:[{},{}]
        result = collection.insert_many(new_collection)
    查询所有的文档 返回的是生成器
        collection.find()
    查询一条文档
        collection.find_one()
    指定条件查询
        collection.find_one({"author": "Mike"})
    对集合内的文档计数：
        collection.count()
        collection.find({"author": "Mike"}).count()
    范围查询:
        collection.find({"date": {"$lt": d}}).sort("author")
        results = collection.find({'age': {'$gt': 20}})
        results = collection.find({'name': {'$regex': '^M.*'}})
    排序：
        results = collection.find().sort('name', pymongo.ASCENDING)
        print([result['name'] for result in results])
    偏移，指定跳过前几个数据；限制，可以指定只要多少个数据
        results = collection.find().sort('name', pymongo.ASCENDING).skip(2).limit(2)
    更新数据
        condition = {'name': 'Kevin'}
        student = collection.find_one(condition)
        student['age'] = 25
        result = collection.update(condition, student)
    删除
        collection.remove({'name': 'Kevin'})

$lt 小于  {'age': {'$lt': 20}}
$gt 大于  {'age': {'$gt': 20}}
$lte    小于等于    {'age': {'$lte': 20}}
$gte    大于等于    {'age': {'$gte': 20}}
$ne 不等于 {'age': {'$ne': 20}}
$in 在范围内    {'age': {'$in': [20, 23]}}
$nin    不在范围内   {'age': {'$nin': [20, 23]}}


以 $ 开头，如
$set（更新字段）、
$unset(删除字段)、
$inc(自增或自减)、
$and、$or、$in、$nin、$nor、$exists（用于判断文档中是否包含某字段）、
$push(向数组中尾部添加一个元素)、
$pushAll(将数组中的所有值push)、
$addToSet（向set集合中添加元素）、
$pop(删除数组中的头部或尾部元素)，
$pull(删除数组中指定的值)、
$size（根据数组的长度进行筛选）、
$slice(返回数组中部分元素，如前几个、后几个、中间连续几个元素)、
$elemMatch(用于匹配数组中的多个条件)、
$where(自定义筛选条件，效率比较低，需要将bson转为js对象，不能使用索引，可以先使用普通查询过滤掉部分不满足条件的文档，然后再使用where，尽量减少where操作文档的数量过大)

"""

import time
import sys
sys.path.append('../../easyQuantify')
from DataEngine.Data import get_stock_list_date, pro
from Config.Config import Config
config = Config('mongo').getInfo()
import pymongo
import random
import requests
import datetime
client = pymongo.MongoClient("mongodb://%s:%s@%s:%s/%s?authSource=admin&authMechanism=SCRAM-SHA-1"
                             %(config['user'], config['password'], config['host'], config['port'],config['db']))
# client =  pymongo.MongoClient(config['host'], config['port'])
db = client[config['db']]
# db.authenticate(config['user'], config['password'])


today  = str(datetime.date.today()).replace('-','')
all_days = pro.query('trade_cal', start_date='20171231', end_date=today)
days = list(all_days[all_days['is_open']==1]['cal_date'])
code_listdate = get_stock_list_date(True)
codes = code_listdate.keys()

def get_dict(trade_day, c):
    # 请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36"
    }
    response = requests.get(
        "https://opensourcecache.zealink.com/cache/dealday/day/%s/%s.json" % (trade_day, c),
        headers=headers
    )
    time.sleep(0.1)
    try:
        clearData = eval(response.text)
    except Exception as e:
        print("【Error】 Day：%s, Stock:%s, " % (trade_day, c))
        time.sleep(2)
        clearData={}
    return clearData

def test():
    for c in codes:
        count = 0
        pre = '20171231'
        start = time.clock()
        for trade_day in days:
            if trade_day<code_listdate[c]:
                continue
            count += 1
            if count %30 == 0:
                time.sleep(random.randint(0,5)/10)
                print("TickData of %s From %s To %s is Downloaded..." % (c, pre, trade_day))
                pre = trade_day
            if count%300==0:
                time.sleep(2+random.randint(-2,2))
        data = []
        print("【====TickData of %s is Downloaded...====】\n【====Length:%s, Time Usage:%s====】" % (c, len(data), round((time.clock()-start)/3600,4)))


def get_Tick_data():
    existCol = list(db.collection_names(include_system_collections=False))
    for c in codes:
        if c in existCol and existCol.index(c) < len(existCol) - 1:
            continue
        col = db[c]
        data = []
        count = 0
        pre = '20171231'
        start = time.clock()
        for trade_day in days:
            if trade_day<code_listdate[c]:
                continue
            if col.find_one({"date":int(trade_day)}):
                continue
            clearData = get_dict(trade_day, c)
            if len(clearData) !=7:
                continue
            count += 1
            data.append(clearData)
            if count %30 == 0:
                if random.randint(0,100)%23==0:
                    time.sleep(random.randint(5, 10) )
                else:
                    time.sleep(random.randint(0,3)/10)
                print("【%s】 TickData of %s From %s To %s is Downloaded..." % (int(count/30), c, pre, trade_day))
                pre = trade_day
                ids = col.insert_many(data)
                data = []
                time.sleep(1)
        if len(data) > 0:
            ids = col.insert_many(data)
        time.sleep(random.randint(30,80))
        print("TickData of %s is Downloaded...\nLength:%s, Time Usage:%s" % (c, len(data), round((time.clock()-start)/3600,4)))


if __name__ == '__main__':
    while True:
        try:
            get_Tick_data()
        except Exception as e:
            print("中断一次，休息下，免得服务器炸了！")
            time.sleep(300)
