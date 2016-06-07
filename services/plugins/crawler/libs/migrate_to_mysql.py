# -*- coding: utf-8 -*-
import MySQLdb
import datetime

from pymongo import DESCENDING

# from config.settings import BASE_DIR
from config.settings import SQL_DB
from config.settings import SQL_HOST
from config.settings import SQL_PASS
from config.settings import SQL_USER
from core import toLog
from core.db import cursor


def yt_mosted_viewed():
    toLog('Start Migration to MySQL', 'db')

    mydb = MySQLdb.connect(
        SQL_HOST,
        SQL_USER,
        SQL_PASS,
        SQL_DB,
        charset='utf8',
        use_unicode=True
    )
    # mydb.set_character_set('utf8')
    # mydb.query('SET NAMES utf8;')
    # mydb.query('SET CHARACTER SET utf8;')
    # mydb.query('SET character_set_connection=utf8;')
    # mydb.query("set character_set_server=utf8;")
    # mydb.query("set character_set_client=utf8;")
    # mydb.query("set character_set_results=utf8;")
    # mydb.query("set character_set_database=utf8;")
    sql_cursor = mydb.cursor()
    sql_cursor.execute("SET NAMES utf8;")
    sql_cursor.execute("SET CHARACTER SET utf8;")
    sql_cursor.execute("SET character_set_connection=utf8;")

    query = "ALTER DATABASE `newdatabase` CHARACTER SET 'utf8' COLLATE"
    query += " 'utf8_unicode_ci'"
    sql_cursor.execute(query)
    mydb.commit()

    query = "ALTER TABLE songs_chart MODIFY COLUMN YTDESCRIPTION"
    query += " varchar(500) DEFAULT '' CHARACTER SET utf8"
    query += " COLLATE utf8_general_ci;"
    sql_cursor.execute(query)
    mydb.commit()

    query = "ALTER TABLE songs_chart MODIFY COLUMN YTTitle"
    query += " varchar(500) DEFAULT '' CHARACTER SET utf8"
    query += " COLLATE utf8_general_ci NOT NULL;"
    sql_cursor.execute(query)
    mydb.commit()

    query = "ALTER TABLE songs_chart MODIFY COLUMN Song"
    query += " varchar(500) DEFAULT '' CHARACTER SET utf8"
    query += " COLLATE utf8_general_ci NOT NULL;"
    sql_cursor.execute(query)
    mydb.commit()

    query = "ALTER TABLE songs_chart MODIFY COLUMN Artist"
    query += " varchar(500) DEFAULT '' CHARACTER SET utf8"
    query += " COLLATE utf8_general_ci NOT NULL;"
    sql_cursor.execute(query)
    mydb.commit()

    _date = datetime.datetime.now().replace(hour=4, minute=30)
    # last_date = _date - datetime.timedelta(days=1)
    _date = _date - datetime.timedelta(days=1)
    last_date = _date - datetime.timedelta(days=2)

    criteria = {
        "$or": [
            {
                "update_video_data": {
                    "$gt": _date
                },
                "daily_views_yesterday": {
                    "$gt": 0
                }
            },
            {
                "published_at": {
                    "$gt": last_date
                }
            }
        ]
    }

    sql_column = {
        'published_at': 'ReleaseDate',
        'href': 'YTURL',
        'dislikes': 'YTDisLikes',
        'likes': 'YTLikes',
        'id': 'YTVideoID',
        'daily_views_today': 'YTDailyViews',
        'title': 'YTTitle',
        'comment_count': 'YTComments',
        'channel_title': 'YTChannel',
        'description': 'YTDescription',
        'daily_views_yesterday': 'YTDailyViewsYest',
        'channel_id': 'YTChannelID',
        'all_views': 'YTAllTimeViews',
        'category_name': 'YTCategory',
        'song_title': 'Song',
        'artist': 'Artist'
    }

    extra_int_columns = [
        'Met',
        'Flag',
        'Cover',
        'Favorite',
        'Listened_To',
        'Omit'
    ]

    extra_str_columns = [
        'Brand_new_artist',
        'Total',
        'Brand_new_song',
        'Tags',
        'Album',
        'Chart_name',
        'Genre',
        'Label',
        'Charts_today',
        'Charts_today_type',
        'Manager',
        'Agent',
        'Lawyer',
        'Notes',
        'Negotiation',
        'Playlist',
        'Price',
        'Chart_name_2'
    ]

    projection = {}
    for i in sql_column.keys():
        projection[i] = 1

    data = cursor.refined_data.find(
        criteria,
        projection,
        no_cursor_timeout=True
    )
    data = data.sort('daily_views_today', DESCENDING).limit(50000)
    # path = BASE_DIR + '/cache/' + '{0}.csv'.format(_date.date())

    if data:

        count = 1
        for doc in data:
            new_doc = {}

            for k, v in doc.items():
                if k != '_id':
                    if k == 'published_at':
                        new_doc[sql_column[k]] = str(v.date())

                    else:
                        if isinstance(v, int):
                            new_doc[sql_column[k]] = v

                        elif isinstance(v, float):
                            new_doc[sql_column[k]] = v

                        elif isinstance(v, long):
                            new_doc[sql_column[k]] = v

                        else:
                            if k == 'description':
                                if isinstance(v, basestring):
                                    text = v[:50].encode('utf8')
                                    text += ' ...'
                                    new_doc[sql_column[k]] = text

                                else:
                                    text = unicode(v[:50]).encode('utf8')
                                    text += ' ...'
                                    new_doc[sql_column[k]] = text

                            else:
                                if isinstance(v, basestring):
                                    text = v.encode('utf8')
                                    new_doc[sql_column[k]] = text

                                else:
                                    text = unicode(v).encode('utf8')
                                    new_doc[sql_column[k]] = text

            for item in extra_str_columns:
                new_doc[item] = ""

            for item in extra_int_columns:
                new_doc[item] = 0

            new_doc['Date'] = datetime.datetime.now().replace(hour=6, minute=0)
            new_doc['Date'] = str(new_doc['Date'].date())
            new_doc['Chart_type'] = 'YouTube'
            new_doc['Rank'] = count

            try:
                table = 'songs_chart'
                # placeholders = ', '.join(['%s'] * len(new_doc))
                # columns = ', '.join(new_doc.keys())
                # sql = "INSERT INTO %s ( %s ) VALUES ( %s )" % (
                #     table,
                #     columns,
                #     placeholders
                # )
                # sql_cursor.execute(sql, new_doc.values())
                sql = insert_from_dict(table, new_doc)
                sql_cursor.execute(sql, new_doc)
                mydb.commit()

            except MySQLdb.IntegrityError as e:
                print str(e)
                qry = 'UPDATE songs_chart SET {}'.format(
                    ', '.join('{}=%s'.format(k) for k in new_doc)
                )
                sql_cursor.execute(qry, new_doc.values())
                mydb.commit()

            except Exception as e:
                print str(e)

            count += 1

    toLog('End Migration to MySQL', 'db')


def insert_from_dict(table, dict):
    """
        Take dictionary object dict and produce sql for
        inserting it into the named table
    """
    sql = 'INSERT INTO ' + table
    sql += ' ('
    sql += ', '.join(dict)
    sql += ') VALUES ('
    sql += ', '.join(map(dict_value_pad, dict))
    sql += ');'
    return sql


def dict_value_pad(key):
    return '%(' + str(key) + ')s'
