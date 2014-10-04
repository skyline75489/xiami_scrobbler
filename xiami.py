#! /usr/bin/env python
# -- encoding:utf - 8 --
import sys
import requests
import re
import time
import logging
from datetime import datetime,timedelta

import gevent
import schedule
from bs4 import BeautifulSoup

from scrobbler import Scrobbler

logger = logging.getLogger()

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:27.0) Gecko/20100101 Firefox/27.0',
           'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
           'Accept-Language': 'zh-cn,zh;q=0.8,en-us;q=0.5,en;q=0.3',
           'Accept-Encoding': 'gzip, deflate',
           'DNT': '1',
           'Connection': 'keep-alive'}

xiami_url = 'http://www.xiami.com/space/charts-recent/u/41714420/'
scrobbler = Scrobbler('skyline75489', '989f9717dce59b6c2f40a6ee940fa95c')

def get_tracks():
    r = requests.get(xiami_url, headers=headers)
    soup = BeautifulSoup(r.content)
    global last_time
    track_times = soup.findAll('td', class_='track_time')
    track_times = [re.search(u'\d+', track_time.text).group()
                for track_time in track_times
                if re.search(u'分钟前', track_time.text)]
    second_html = soup.find('td', class_='track_time')
    if second_html:
        second_exist = re.search(u'秒前|刚刚', second_html.text)
    else:
        second_exist = False
    if track_times or second_exist:
        exists_times = [int(track_time) for track_time in track_times
                  if int(track_time) < 10]
        track_times = [int(track_time) for track_time in track_times
                 if int(track_time) < 5]
        record_time = None
        if track_times:
            record_time = datetime.now() - timedelta(minutes=track_times[0])
            record_time = record_time.strftime('%Y-%m-%d %H:%M:%S')

        track_times = [int(time.time() - track_time * 60)
                 for track_time in track_times]
        if second_exist:
            record_time = datetime.now()
            record_time = record_time.strftime('%Y-%m-%d %H:%M:%S')
            track_times.insert(0, int(time.time()))

        track_number = len(track_times)
        if record_time:
            track_htmls = soup.findAll(
                'tr', id=re.compile('track_\d+'), limit=track_number)
            upper_htmls = [
                track_html.find('td', class_='song_name') for track_html in track_htmls]
            artists_html = [artist_html.findAll('a')[1:] for artist_html in upper_htmls]
            artists = []
            for artist in artists_html:
                all_artists = [one_artist.text for one_artist in artist
                                    if not re.search('http://i.xiami.com',
                                                     one_artist['href'])]
                all_artist = '&'.join(all_artists)
                artists.append(all_artist)
            title_htmls = soup.findAll(
                'a', href=re.compile('/song/\d+'), limit=track_number)
            titles = [title['title'] for title in title_htmls]
            return (titles, artists, track_times, record_time)
        elif exists_times:
            # database.modify_user(user[0], user[2])
            return (None, None, None, None)
        else:
            # database.not_listening(user[0])
            return (None, None, None, None)
    else:
        # database.not_listening(user[0])
        return (None, None, None, None)


def scrobble(title, artist, timestamp):
    print(artist, title, timestamp)
    scrobbler.submit(artist, title, timestamp=timestamp)

def do_scrobble():
    titles, artists, track_times, record_time = get_tracks()
    print(titles, artists, track_times, record_time)
    if titles is not None:
        spawns = [gevent.spawn(scrobble, title, artist, timestamp)
                  for title, artist, timestamp 
                  in zip(titles, artists, track_times)]
        gevent.joinall(spawns)
    
def main():
    scrobbler.handshake()
    schedule.every(5).minutes.do(do_scrobble)
    while True:
        schedule.run_pending()
        time.sleep(30)
    
if __name__ == '__main__':
    main()

        
