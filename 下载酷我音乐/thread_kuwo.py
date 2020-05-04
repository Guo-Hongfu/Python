# 使用多线程下载
import math
import os
import random
import socket
import struct
import time
from queue import Queue
from threading import Thread
from urllib.parse import urlencode
import logging
import requests
logging.basicConfig(format='%(asctime)s -%(levelname)s: %(message)s',
                    level=logging.INFO)

def get_random_ip():
    return socket.inet_ntoa(struct.pack('>I', random.randint(1, 0xffffffff)))


DETAIL_URL = "http://www.kuwo.cn/singer_detail/{0}"
SEARCH_SINGER_URL = "http://www.kuwo.cn/api/www/search/searchArtistBykeyWord?"
SONG_LIST_URL = "http://www.kuwo.cn/api/www/artist/artistMusic?artistid={0}&pn={1}&rn=30"
MP3_URL = "http://www.kuwo.cn/url?format=mp3&rid={0}&response=url&type=convert_url3&br=2000&from=web"
MP4_URL = "http://www.kuwo.cn/url?rid={0}&response=url&format=mp4|mkv&type=convert_url"
HEADERS = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36",
    'Host': "www.kuwo.cn",
}

download_media_urls_queue = Queue(maxsize=10)
save_media_urls_queue = Queue(maxsize=10)
SINGER_INFO = None


class Download(object):
    def make_file_store(self, name):
        project_dir = os.path.dirname('__file__')
        files_store = os.path.join(project_dir, name)
        is_exists = os.path.exists(files_store)
        if not is_exists:
            os.makedirs(files_store)
        return files_store

    def _download(self, file_store, file_link, fix):
        try:
            HEADERS['X-Forwarded-For'] = get_random_ip()
            res = requests.get(file_link, timeout=10, headers=HEADERS, verify=False)
            if 'mp3' == fix:
                data_mp3 = res.json()
                down_item = {"url": data_mp3['url'], "filepath": file_store}
                # return self.__save(down_item)
                save_media_urls_queue.put(down_item)
            if 'mp4' == fix:
                down_mp4_url = res.content.decode()
                down_item = {"url": down_mp4_url, "filepath": file_store}
                # self.__save(down_item)
                save_media_urls_queue.put(down_item)

            return True
        except Exception as err:
            # self.error_item.append(self.item)
            print('None,下载失败--{0},失败原因:{1}'.format(file_store, err))
            return False

    def __save(self, down_item):
        down_url = down_item['url']
        file_store = down_item['filepath']
        HEADERS['X-Forwarded-For'] = get_random_ip()
        print('down_url:{}'.format(down_url))
        res = requests.get(down_url, timeout=50, stream=True, headers=HEADERS)
        with open(file_store, 'wb+') as f:
            for chunk in res.iter_content(chunk_size=512):
                if chunk:
                    f.write(chunk)
        return True


class DownloadMedia(Thread, Download):
    def run(self):
        # 下载资源
        while 1:
            try:
                item = download_media_urls_queue.get()
                file = item['singer'] + "/" + item['fix'] + "/"
                mp4_store = self.make_file_store(file)
                self._download(mp4_store + item['filename'], item['url'], item['fix'])
                print('正在下载 {fix} ：{filename}'.format(fix=item['fix'], filename=item['filename']))
            except IndexError as e:
                print('等待1秒')
                time.sleep(1)

class SaveFile(Thread):
    def run(self):
        sleeptime = 1
        while 1:
            try:
                down_item = save_media_urls_queue.get()
                down_url = down_item['url']
                file_store = down_item['filepath']
                # HEADERS['X-Forwarded-For'] = get_random_ip()
                res = requests.get(down_url, timeout=50, stream=True)
                with open(file_store, 'wb+') as f:
                    for chunk in res.iter_content(chunk_size=512):
                        if chunk:
                            f.write(chunk)
                    # print("{} 下载完成".format(file_store))
                    logging.info("{} 下载完成".format(file_store))

            except Exception as er:
                print('保存文件异常：{}'.format(er))
                sleeptime += 1
                if save_media_urls_queue.empty() and sleeptime > 200:
                    break
                time.sleep(1)


class KuwoSpider(Thread):
    def __init__(self):
        self.singerid = SINGER_INFO['id']
        self.singer = SINGER_INFO['name']
        super().__init__()

    def run(self):
        while 1:

            try:
                self.singerid = SINGER_INFO['id']
                HEADERS['X-Forwarded-For'] = get_random_ip()
                response = requests.get(SONG_LIST_URL.format(self.singerid, 1), headers=HEADERS)
                data = response.json()['data']
                song_list = data.get('list', [])
                self.__parse_song_list(song_list)
                total = data['data']['total']
                page_count = math.ceil(int(total) / 30) + 1
                for i in range(2, page_count):
                    try:
                        HEADERS['X-Forwarded-For'] = get_random_ip()
                        response = requests.get(SONG_LIST_URL.format(self.singerid, i), headers=HEADERS).json()
                        self.__parse_song_list(response['data']['list'])
                    except Exception as e:
                        print('出现异常:{}'.format(SONG_LIST_URL.format(self.singerid, i)))
                break
            except Exception as e:
                print('{}的歌曲列表获取完成,下载中.....'.format(SINGER_INFO['name']))
                print(e)
                break

    def __parse_song_list(self, songlist):
        for song in songlist:
            rid = song['rid']
            file_name = song['name'].replace('/', '_')
            if 1 == int(song['hasmv']):
                download_media_urls_queue.put({
                    "url": MP4_URL.format(rid),
                    "filename": file_name + '.mp4',
                    "singer": self.singer,
                    "fix": "mp4"
                })

            download_media_urls_queue.put({
                "url": MP3_URL.format(rid),
                "filename": file_name + ".mp3",
                "singer": self.singer,
                "fix": "mp3"
            })


def get_singer_info(singer=None):
    HEADERS['X-Forwarded-For'] = get_random_ip()
    response = requests.get(DETAIL_URL.format(336), headers=HEADERS)
    token = response.cookies['kw_token']
    HEADERS['Cookie'] = "kw_token={0}".format(token)
    HEADERS['csrf'] = token
    param = urlencode({"key": singer})
    url = SEARCH_SINGER_URL + param
    HEADERS['Referer'] = url
    HEADERS['X-Forwarded-For'] = get_random_ip()
    response = requests.get(url, headers=HEADERS).json()
    return response['data']['list'][0]


if __name__ == '__main__':
    keyword = input('请输入歌手名字：')
    print("搜索歌手：{} 的信息：".format(keyword))
    # singer = "周杰伦"
    while 1:
        try:
            SINGER_INFO = get_singer_info(keyword)
            print("获取到歌手 `{singer}`的信息，歌曲数量:{num}".format(singer=SINGER_INFO['name'], num=SINGER_INFO['musicNum']))
            next_to = input("是否开始下载？（Y:是，N:否）：")
            if next_to.upper() == 'Y':
                kuwoSpider = KuwoSpider()
                kuwoSpider.start()
                download = DownloadMedia()
                download.start()
                savefile = SaveFile()
                savefile.start()
                print('`{singer}`的歌曲全部下载完成~！~'.format(singer=SINGER_INFO['name']))
                break
            keyword = input('请重新输入歌手名字：')
        except Exception as e:
            print('未搜索到 {} 歌手的信息，请重新输入'.format(keyword))
            print(e)
            keyword = input('请输入歌手名字：')
