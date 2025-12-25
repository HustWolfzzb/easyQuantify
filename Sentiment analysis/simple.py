import sys
sys.path.append('../../easyQuantify')
import pandas as pd
from DataEngine.Data import pro
import jieba
import datetime
import time
import os
def get_CFSD():
    pos_neg_word = pd.read_excel('../../easyQuantify/Sentiment analysis/Li_CFSD_list.xlsx')
    pos_word = []
    neg_word = []
    for x in range(len(pos_neg_word)):
        if pos_neg_word.iloc[x]['sentiment'] == 1:
            pos_word.append(pos_neg_word.iloc[x]['word'])
        else:
            neg_word.append(pos_neg_word.iloc[x]['word'])
    return pos_word, neg_word

pos_word, neg_word = get_CFSD()

def pos_senti(content):
    """
    content: 待分析文本内容
    返回正面词占文本总词语数的比例
    """
    try:
        pos_word_num = 0
        words = jieba.lcut(content)
        for kw in pos_word:
            pos_word_num += words.count(kw)
        return pos_word_num/len(words)
    except:
         return 0

def neg_senti(content):
    """
    content: 待分析文本内容
    返回负面词占文本总词语数的比例
    """
    try:
        neg_word_num = 0
        words = jieba.lcut(content)
        for kw in neg_word:
            neg_word_num += words.count(kw)
        return neg_word_num/len(words)
    except:
        return 0


def apply(newsdata):
    newsdata['pos']=newsdata['content'].agg(pos_senti)
    newsdata['neg']=newsdata['content'].agg(neg_senti)

def saveNews(source='sina'):
    start = max([int(x[:x.find('.')].replace('-','')) for x in os.listdir(source) if x.find('csv')!=-1])
    print("Folder:%s, 现在存在的最后一天的新闻：%s\n"%(source,start))
    today  = str(datetime.date.today()).replace('-','')
    for i in range(5):
        breakout = False
        s = start + i*10000
        e = s + (i+1)*10000
        if e>int(today):
            e = int(today)
            breakout = True
        if e-s<1:
            return
        days = list(pro.query('trade_cal', start_date=str(s), end_date=str(e))['cal_date'])
        print("更新数据，从%s-%s"%(days[0],days[-1]))
        for day in days:
            try:
                day = day[:4] +'-' + day[4:6] + '-' + day[6:]
                # if day+'.csv' in os.listdir(source):
                #     continue
                newsdata_morning = pro.news(src=source, start_date=day+' 00:00:00', end_date=day+' 11:59:59')
                time.sleep(30)
                if len(newsdata_morning)<10:
                    continue
                apply(newsdata_morning)
                newsdata_afternoon = pro.news(src=source, start_date=day+' 12:00:00', end_date=day+' 23:59:59')
                time.sleep(30)
                apply(newsdata_afternoon)
                pos_news = newsdata_morning.append(newsdata_afternoon)
                neg_news = pos_news.copy(deep=True)
                print("Source:%s DATE:%s NEWS NUM:%s"%(source, day, len(pos_news)), end=',')
                pos_news = pos_news[(pos_news['pos']-pos_news['neg']) > pos_news['pos'] * 0.8]
                pos_news = pos_news[pos_news['pos'] > 0.05]
                neg_news = neg_news[(neg_news['neg']-neg_news['pos']) > neg_news['neg'] * 0.8]
                neg_news = neg_news[neg_news['neg']> 0.05]
                print("AFTER CLEAN,POS NEWS:%s ，NEG NEWS:%s, TOTAL:%s"%(len(pos_news), len(neg_news), len(pos_news)+len(neg_news)))
                newsdata = pos_news.append(neg_news)

                newsdata.to_csv(source+'/'+day+'.csv',index=False)
            except Exception as e:
                print(e)
                time.sleep(60)
        if breakout:
            break


if __name__ == '__main__':
    source = ['sina', '10jqka', 'eastmoney', 'yuncaijing']
    for sou in source:
        saveNews(sou)