import getopt
import math
import os
import sys
from multiprocessing import Process

import requests

"""
无更新内容，提交只祝贺祖国七十周岁生日快乐，越来越强大。
"""

class Kuwo(object):
    """
    下载mp3和mp4
    """

    def __init__(self, artistid, singer, timerer):
        self.item = {}
        self.error_item = []
        self.artistid = artistid
        self.singer = singer
        self.timerer = timerer
        self.detail_url = "http://www.kuwo.cn/singer_detail/{0}"
        self.song_list_url = "http://www.kuwo.cn/api/www/artist/artistMusic?artistid={0}&pn={1}&rn=30"
        self.mp3_url = "http://www.kuwo.cn/url?format=mp3&rid={0}&response=url&type=convert_url3&br=2000&from=web"
        self.mp4_url = "http://www.kuwo.cn/url?rid={0}&response=url&format=mp4|mkv&type=convert_url"
        self.headers = {
            'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.131 Safari/537.36",
            'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'Host': "www.kuwo.cn",
        }

    def go(self):
        token = self.get_token(self.artistid)
        self.headers['Cookie'] = "kw_token={0}".format(token)
        self.headers['csrf'] = token

        response = requests.get(self.song_list_url.format(self.artistid, 1), headers=self.headers)
        data = response.json()
        if 200 == data['code']:
            total = data['data']['total']
            page_count = math.ceil(int(total) / 30) + 1

            # pool = Pool()
            for i in range(1, page_count):
                response = requests.get(self.song_list_url.format(self.artistid, i), headers=self.headers)
                data = response.json()
                song_list = data['data']['list']
                self.process_song(song_list)
                # p = Process(target=self.process_song, args=[song_list])
                # p.start()
                print('开始下载第{0}页歌曲,共{1}首'.format(i, len(song_list)))
        else:
            print('无法访问酷我音乐')
        # 下载失败的重新下载
        while len(self.error_item) != 0:
            print('重新下载失败的歌曲:')
            self.process_song(self.error_item)
        print('下载完成')

    """
    获取csrf
    """
    def get_token(self,singer_id):
        response = requests.get(self.detail_url.format(singer_id),headers=self.headers)
        return response.cookies['kw_token']


    def process_song(self, song_list):
        """
        解析歌曲列表
        :param song_list:
        :return:
        """
        for song in song_list:
            self.item = {}
            self.item['file_path'] = self.singer
            rid = song['rid']
            self.item['artist'] = song['artist']
            self.item['song_name'] = song['name']
            self.item['song_mp4'] = self.mp4_url.format(rid) if 1 == int(song['hasmv']) else None
            self.item['song_mp3'] = self.mp3_url.format(rid)
            s = float(song['songTimeMinutes'].replace(':', '.'))
            if s >= self.timerer:
                res = self.process_item()
                if self.error_item:
                    if res is True and self.item in self.error_item:
                        self.error_item.remove(self.item)

    def process_item(self):
        mp3res = mp4res = False
        if self.item['song_mp3'] is not None:
            mp3res = self._download_mp3()
        if self.item['song_mp4'] is not None:
            mp4res = self._download_mp4()
        return mp3res and mp4res

    def _download_mp3(self):
        file = self.item['file_path'] + '/mp3/'
        file_store = self._make_file_store(file)
        file_store = file_store + self.item['song_name'] + '.mp3'
        con_text = self._download(file_store, self.item['song_mp3'], 'mp3')
        print('下载完：{0}--MP3'.format(self.item['song_name']))
        return con_text

    def _download_mp4(self):
        file = self.item['file_path'] + '/mp4/'
        mp4_store = self._make_file_store(file)
        file_store = mp4_store + self.item['song_name'] + '.mp4'
        con_text = self._download(file_store, self.item['song_mp4'], 'mp4')
        print('下载完：{0} MP4'.format(self.item['song_name']))
        return con_text

    def _make_file_store(self, name):
        project_dir = os.path.dirname('__file__')
        files_store = os.path.join(project_dir, name)
        is_exists = os.path.exists(files_store)
        if not is_exists:
            os.makedirs(files_store)
        return files_store

    def _download(self, file_store, file_link, fix):
        try:
            res = requests.get(file_link, timeout=10, headers=self.headers)
            if 'mp3' == fix:
                data_mp3 = res.json()
                self._save(data_mp3['url'], file_store)
            if 'mp4' == fix:
                down_mp4_url = res.content.decode()
                self._save(down_mp4_url, file_store)
            return True
        except:
            self.error_item.append(self.item)
            print('None,下载失败--{0}'.format(self.item['song_name']))
            return False

    def _save(self, down_url, file_store):
        res = requests.get(down_url, timeout=50)
        with open(file_store, 'wb') as f:
            f.write(res.content)


def _get_arg(opts, op, default):
    val = [arg for (opt, arg) in opts if opt == op]
    return default if 0 == len(val) else val[0]


if __name__ == '__main__':
    argv = sys.argv[1:]
    try:
        opts, args = getopt.getopt(argv, "i:f:t:", ["ifile=", "ffile=", "tfile="])
    except getopt.GetoptError:
        print('kuwo.py -i <artisid> -f <singer> -t <min song timer>')
        sys.exit(2)
    artid = _get_arg(opts, '-i', 1486611)
    singer = _get_arg(opts, '-f', '陈雪凝')
    timerer = _get_arg(opts, '-t', 2.5)
    kuwo = Kuwo(artid, singer, float(timerer))
    kuwo.go()

