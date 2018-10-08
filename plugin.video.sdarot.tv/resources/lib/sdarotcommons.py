# -*- coding: utf-8 -*-

import requests, time, os, re, sqlite3, urllib, urllib2, base64, urlparse, json, io
from xbmcswift2 import Plugin, xbmc, xbmcgui
plugin = Plugin()

try:
    from urllib3.util import connection
except:
    plugin.log.error("'script.module.urllib3' not installed.")
    from requests.packages.urllib3.util import connection
    plugin.log.error("try to use 'requests.packages.urllib3' instead.")

__PLUGIN_VERSION__ = plugin.addon.getAddonInfo('version')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36 Sdarot/' + __PLUGIN_VERSION__
}

FANART = plugin.addon.getAddonInfo('fanart')
ICON = plugin.addon.getAddonInfo('icon')
API = base64.decodestring('aHR0cHM6Ly9hcGkuc2Rhcm90LnR2')
POSTER_PREFIX = base64.decodestring('aHR0cHM6Ly93d3cuZG9tYWluNGtvZGkubGlmZS9zZXJpZXMv')
CACHE_FILE = os.path.join(xbmc.translatePath(plugin.addon.getAddonInfo('profile')).decode('utf-8'), 'cache.json')


def get_ip(address):
    handlers = [
        urllib2.HTTPHandler(),
        urllib2.HTTPSHandler()
    ]
    opener = urllib2.build_opener(*handlers)
    req = urllib2.Request(base64.decodestring('aHR0cHM6Ly9kbnMuZ29vZ2xlLmNvbS9yZXNvbHZlP25hbWU9')+address)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36')
    try:
        response = opener.open(req,timeout=100)
        data = response.read()
        response.close()
    except Exception as ex:
        plugin.log.error(ex)
        return None
    data = json.loads(data)
    return data['Answer'][0]['data']


def cache_ip(address):
    try:
        if not os.path.isfile(CACHE_FILE):
            a_list = {}
        else:
            with open(CACHE_FILE, 'r') as handle:
                a_list = json.load(handle)
        a_key = base64.encodestring(urlparse.urlparse(address).netloc)
        if not a_list.get(a_key):
            a_list[a_key] = {'a': 0, 'b': ''}
        now = int(time.time())
        if now - a_list[a_key]['a'] > 86400:
            a_list[a_key]['b'] =  base64.encodestring(get_ip(base64.decodestring(a_key)))
            a_list[a_key]['a'] =  now
            with io.open(CACHE_FILE, 'w', encoding='utf-8') as handle:
                handle.write(unicode(json.dumps(a_list, ensure_ascii=False)))
        return base64.decodestring(a_list[a_key]['b'])
    except Exception as ex:
        plugin.log.error(ex)
        return None


_orig_create_connection = connection.create_connection

def patched_create_connection(address, *args, **kwargs):
    host, port = address
    return _orig_create_connection((cache_ip(API), port), *args, **kwargs)

connection.create_connection = patched_create_connection


def get_user_cookie():
    username = plugin.get_setting('username')
    password = plugin.get_setting('password')

    if username and password:

        data = {
            'username': username,
            'password': password
        }

        req = requests.post(API + '/login', data=data, headers=HEADERS)
        res = req.json()

        if res['success']:
            return req.cookies.get_dict()

        else:
            xbmcgui.Dialog().ok('נסיון התחברות נכשל, סיסמא אופסה', ', '.join(res['errors']).encode('utf-8'))
            plugin.set_setting('password', '')

    return {}


def make_item(label, path, plot, poster, is_playable, year='', genres=None,
              sid=None, episode=None, season=None, fav='', watched='0',
              updated_list=None, is_user=False, sync_storage=None):

    year = u'שנת יציאה: ' + year if year else ''
    genres = u"ז'אנר: " + string_genres(genres) if genres else ''

    item = {
        'label': label,
        'path': path,
        'is_playable': is_playable,
        'icon': poster,
        'thumbnail': poster,
        'info': {
            'plot': plot + '\n\n' + year + '\n\n' + genres
        },
        'properties': {
            'Fanart_Image': FANART
        },
        'context_menu': [('הוספה למועדפים סדרות', 'XBMC.Container.Update({0})'.format(fav))]
    }

    vid_details = '{0}/{1}/{2}'.format(sid, season, episode)
    if str(watched) == '1':
        item['info']['playcount'] = '1'
        if not updated_list.get(vid_details):
            updated_list[vid_details] = '1'
            query = "UPDATE files SET playCount=1 WHERE strFilename LIKE" \
                    " 'plugin://plugin.video.sdarot.tv/watch/{0}%'".format(vid_details)
            db_path = get_movies_db()
            conn = sqlite3.connect(db_path)
            conn.execute(query)
            conn.commit()
            conn.close()
    else:
        if is_user:
            sync_storage = sync_storage
            try:
                if sync_storage.get(vid_details):
                    del sync_storage[vid_details]
                    query = "UPDATE files SET playCount=null WHERE strFilename LIKE" \
                            " 'plugin://plugin.video.sdarot.tv/watch/{0}%'".format(vid_details)
                    db_path = get_movies_db()
                    conn = sqlite3.connect(db_path)
                    conn.execute(query)
                    conn.commit()
                    conn.close()
            except AttributeError:
                sync_storage['vids'] = {}

    return item


def get_final_video_and_cookie(sid, season, episode, choose_quality=False, download=False):
    cookie = get_user_cookie()
    req = requests.post(API + '/episode/preWatch', data={'SID': sid, 'season': season, 'episode': episode},
                        cookies=cookie, headers=HEADERS)
    token = req.text
    if not cookie:
        cookie = req.cookies.get_dict()

    if token == 'donor':
        vid = get_video_url(sid, season, episode, token, cookie, choose_quality)

    else:
        if download:
            plugin.notify('התחבר כמנוי כדי להוריד פרק זה', image=ICON)
            return None, None
        else:
            dp = xbmcgui.DialogProgress()
            dp.create("לצפייה באיכות HD וללא המתנה ניתן לרכוש מנוי", "אנא המתן 30 שניות", '',
                      "[COLOR orange][B]לרכישת מנוי להיכנס בדפדפן - www.sdarot.tv/donate[/B][/COLOR]")
            dp.update(0)
            for s in range(30, -1, -1):
                time.sleep(1)
                dp.update(int((30 - s) / 30.0 * 100), "אנא המתן 30 שניות", 'עוד {0} שניות'.format(s), '')
                if dp.iscanceled():
                    dp.close()
                    return None, None

        vid = get_video_url(sid, season, episode, token, cookie, choose_quality)

    if vid:
            return vid, cookie


def get_video_url(sid, season, episode, token, cookie, choose_quality):
    req = requests.post(API + '/episode/watch/sid/{0}/se/{1}/ep/{2}'.format(sid, season, episode),
                        data={'token': token}, cookies=cookie, headers=HEADERS).json()
    if req['success']:
        qualities = req['watch']
        if choose_quality:
            return qualities
        else:
            qualities_list = qualities.keys()
            max_quality = int(plugin.get_setting('max_quality'))
            quality = '480'

            if max_quality >= 720:
                quality = '1080' if '1080' in qualities_list and max_quality == 1080 else '720'
                if quality == '720' and '720' not in qualities_list:
                    quality = '480'

            return build_final_url(qualities[quality], cookie)


def get_ip_url(url):
    base = urlparse.urlparse(url)
    watch = cache_ip(url)
    return url.replace(base.netloc, watch)

def build_final_url(url, cookie):
    return 'http:{0}|Cookie=Sdarot={1}&User-Agent={2}'.format(get_ip_url(url), urllib.quote(cookie.get('Sdarot'), safe=''), HEADERS.get('User-Agent'))


def set_dir(items, mode, content, p):
    p.add_items(items)
    p.set_content(content)
    p.set_view_mode(mode)


def sync_sdarot(storage, updated_list):
    """
    :param storage: -> Dictionary of all the videos that has been already synced.
    :param updated_list: -> Dictionary of all videos that needs to be updated from the server.
    :return:
    """
    cookie = get_user_cookie()
    if cookie != {}:
        try:
            db_path = get_movies_db()
            conn = sqlite3.connect(db_path)
            c = conn.cursor()
            c.execute('SELECT idFile, strFilename, idPath FROM files WHERE strFilename LIKE'
                      ' "plugin://plugin.video.sdarot.tv/watch%" AND playCount > 0')
            db_list = c.fetchall()
            db_ids = []
            db_video_details = []  # Compare against updated_list (that gets updated on make_item)
            reg = re.compile('(\d{1,10})/(\d{1,4})/(\d{1,4})')
            ref_list = storage.keys()  # Reference list of already synced episodes

            for vid in db_list:
                _id = vid[0]
                path = vid[1]
                details = re.search(reg, path)
                db_ids.append(_id)
                vid_details = '{0}/{1}/{2}'.format(details.group(1), details.group(2), details.group(3))
                db_video_details.append(vid_details)
                if _id not in ref_list:
                    ref = {
                        '_id': _id,
                        'path': path,
                        'playCount': vid[2],
                        'vid': {
                            'serie': details.group(1),
                            'season': details.group(2),
                            'episode': details.group(3),
                            'watched': 'true'
                        }
                    }
                    requests.post(API + '/episode/markAS', data=ref['vid'], cookies=cookie, headers=HEADERS)
                    storage[ref['_id']] = ref
                    storage['vids'][vid_details] = '1'

            for _id in ref_list:
                if _id != 'vids' and _id not in db_ids:  # User has marked video as unwatched
                    ref = storage[_id]
                    ref['vid']['watched'] = 'false'
                    requests.post(API + '/episode/markAS', data=ref['vid'], cookies=cookie, headers=HEADERS)
                    storage.pop(_id)
                    vid_details = '{0}/{1}/{2}'.format(ref['vid']['serie'], ref['vid']['season'], ref['vid']['episode'])
                    storage['vids'][vid_details] = '1'

            id_path = c.execute("""SELECT idPath FROM 'path' WHERE strPath LIKE
                                'plugin://plugin.video.sdarot.tv/'""").fetchone()[0]
            for vd in updated_list.keys():
                if vd not in db_video_details:  # User might have marked as unwatched, check if exists
                    path = 'plugin://plugin.video.sdarot.tv/watch/{0}/'.format(vd)
                    c.execute('SELECT idFile, strFilename, playCount FROM files WHERE strFilename LIKE'
                              ' "{0}%"'.format(path))
                    if not c.fetchone():  # We need to update kodi's database manually
                        details = re.search(reg, vd)
                        req = requests.get(API + '/series/info/{0}'.format(details.group(1))).json()['serie']
                        item_path = path + urllib.quote_plus(req['heb'].encode('utf8')) + '/None'
                        c.execute("""INSERT INTO files (idPath, strFilename, playCount) VALUES (?,?,1);""",
                                  (id_path, item_path))
                        conn.commit()
                    else:  # Not in db_video_details because playCount == 0, we need to update the server
                        details = re.search(reg, vd)
                        vid = {
                            'serie': details.group(1),
                            'season': details.group(2),
                            'episode': details.group(3),
                            'watched': 'false'
                        }
                        requests.post(API + '/episode/markAS', data=vid, cookies=cookie, headers=HEADERS)

                    storage['vids'][vd] = '1'

            updated_list.clear()
            conn.close()
            return True
        except Exception as ex:
            plugin.log.error(ex)


def get_movies_db():
    db_path = xbmc.translatePath('special://database')
    for db in os.listdir(db_path):
        if db.startswith('MyVideos'):
            return db_path + '/' + db


def buttons_factory(label, path):
    label = '[COLOR yellow]{0}[/COLOR]'.format(label)
    return make_item(label, path, '', FANART, False)


def string_genres(genres):
    if type(genres) is str:
        return genres.decode('utf8')

    s = ''
    for g in genres:
        s += g['name'] + ', '
    return s[:-2]
