# Python Import
import bs4
import datetime
import requests
import time
import random
import urlparse

from pymongo.errors import DuplicateKeyError

from apiclient.discovery import build

# YouTube Crawler Import
from config.settings import DEVELOPER_KEY
from config.settings import YOUTUBE_API_SERVICE_NAME
from config.settings import YOUTUBE_API_VERSION
from config.settings import period_days
from core import toLog
from core.db import cursor


def build_youtube_api():
    youtube = build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=DEVELOPER_KEY
    )

    return youtube


def executor_crawl(_to, _from, criteria, next_page_token=None):
    msg = 'Start executer:---> start: {0} | end: {1}'.format(_from, _to)
    msg += " criteria: {0} | next_page: {1}".format(criteria, next_page_token)
    toLog(msg, 'jobs')

    youtube = build_youtube_api()

    # Call the search.list method to retrieve results matching the specified
    # query term.
    if next_page_token:
        search_response = youtube.search().list(
            q=criteria['q'],
            maxResults=criteria['max_results'],
            part="id,snippet",
            type='video',
            order='viewCount',
            pageToken=next_page_token,
            videoCategoryId='10',  # Music & Entertaiment Category
            publishedAfter=_from.strftime('%Y-%m-%dT%H:%M:%SZ'),
            publishedBefore=_to.strftime('%Y-%m-%dT%H:%M:%SZ'),
        ).execute()

    else:
        search_response = youtube.search().list(
            q=criteria['q'],
            maxResults=criteria['max_results'],
            part="id,snippet",
            type='video',
            order='viewCount',
            videoCategoryId='10',  # Music & Entertaiment Category
            publishedAfter=_from.strftime('%Y-%m-%dT%H:%M:%SZ'),
            publishedBefore=_to.strftime('%Y-%m-%dT%H:%M:%SZ'),
        ).execute()

    # Add each result to the appropriate list, and then display the lists of
    # matching videos, channels, and playlists.
    for search_result in search_response.get("items", []):
        _video = {'created_date': datetime.datetime.now()}

        if search_result["kind"] == "youtube#video":
            _video['href'] = 'https://www.youtube.com/watch?v='
            _video['img'] = search_result['snippet']['thumbnails']['default']
            _video['title'] = search_result['snippet']['title']
            _video['channel_id'] = search_result['snippet']['channelId']
            _video['channel_title'] = search_result['snippet']['channelTitle']
            _video['published_at'] = search_result['snippet']['publishedAt']
            _video['description'] = search_result['snippet']['description']

            if 'id' in search_result['snippet']:
                _video['href'] += search_result['snippet']['id']['videoId']
                _video['id'] = search_result['snippet']['id']['videoId']

            else:
                _video['href'] += search_result['id']['videoId']
                _video['id'] = search_result['id']['videoId']

            try:
                result = cursor.refined_data.insert(_video)

            except DuplicateKeyError:
                result = True
                toLog("Crawling Error: It can't be save record", 'error')

            if not result:
                toLog("Crawling Error: It can't be save record", 'error')

        elif search_result["kind"] == "youtube#searchResult":
            _video['href'] = 'https://www.youtube.com/watch?v='
            _video['img'] = search_result['snippet']['thumbnails']['default']
            _video['title'] = search_result['snippet']['title']
            _video['channel_id'] = search_result['snippet']['channelId']
            _video['channel_title'] = search_result['snippet']['channelTitle']
            _video['published_at'] = search_result['snippet']['publishedAt']
            _video['description'] = search_result['snippet']['description']

            if 'id' in search_result['snippet']:
                _video['href'] += search_result['snippet']['id']['videoId']
                _video['id'] = search_result['snippet']['id']['videoId']

            else:
                _video['href'] += search_result['id']['videoId']
                _video['id'] = search_result['id']['videoId']

            try:
                result = cursor.refined_data.insert(_video)

            except DuplicateKeyError:
                result = True
                toLog("Crawling Error: It can't be save record", 'error')

            if not result:
                toLog("Crawling Error: It can't be save record", 'error')

        else:
            toLog("UnHandled Crawling: {0}".format(search_result), 'debug')

        if not result:
            toLog("Crawling Error: It can't be save record", 'error')

    # Create Next Page
    next_page_token = search_response.get("nextPageToken")

    msg = 'End executer:---> start: {0} | end: {1}'.format(_from, _to)
    msg += " criteria: {0} | next_page: {1}".format(criteria, next_page_token)
    toLog(msg, 'jobs')

    return next_page_token


def divide_datetime(period_years):
    now = datetime.datetime.now()
    last = now - datetime.timedelta(days=period_years * 365)

    all_months = period_years * 12
    month_list = [now]
    tuple_month_list = []

    for month in range(1, all_months + 1):
        new = now - datetime.timedelta(days=month * period_days)
        tuple_month_list.append((month_list[-1], new))
        month_list.append(new)

    tuple_month_list.append((month_list[-1], last))

    return tuple_month_list


def execute_batch(_from, _to, criteria):

    flag = True
    next_page = None
    time_list = [2, 2.12, 3, 2.2, 2.75, 2.6, 1.1, 2.31, 2.5]

    while flag:

        try:
            next_page = executor_crawl(_to, _from, criteria, next_page)
            time.sleep(random.choice(time_list))

        except Exception as e:
            print e
            toLog(str(e), 'jobs')
            flag = False


def crawl_search(keyword, page):
    if ' ' in keyword:
        keyword = keyword.replace(' ', '+')

    url = 'https://www.youtube.com/results?search_sort=video_view_count'
    # url += '&filters=today'
    url += '&search_query=' + keyword
    url += '&page={0}'.format(page)

    text = requests.get(url).text
    soup = bs4.BeautifulSoup(text, "html.parser")

    div = []

    for d in soup.find_all('div'):

        if d.has_attr('class') and 'yt-lockup-dismissable' in d['class']:
            div.append(d)

    for d in div:
        doc = {'created_date': datetime.datetime.now()}
        img0 = d.find_all('img')[0]
        a0 = d.find_all('a')[0]

        if not img0.has_attr('data-tumb'):
            doc['img'] = img0['src']

        else:
            doc['img'] = img0['data-tumb']

        a0 = [x for x in d.find_all('a') if x.has_attr('title')][0]
        doc['title'] = a0['title']
        doc['href'] = 'https://www.youtube.com' + a0['href']
        doc['id'] = get_video_id(doc['href'])

        try:
            result = cursor.refined_data.insert(doc)

        except DuplicateKeyError:
            result = True
            toLog("Crawling Error: It can't be save record", 'error')

        if not result:
            toLog("Crawling Error: It can't be save record", 'error')


def get_video_id(url):
    url_data = urlparse.urlparse(url)
    query = urlparse.parse_qs(url_data.query)
    video = query["v"][0]
    return video
