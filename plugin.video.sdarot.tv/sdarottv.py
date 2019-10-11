# -*- coding: utf-8 -*-

""""
created on 30/04/2011
updated on 2/10/2017

@author: Shai, updated by Roey
"""

import requests, uuid, threading, os, urllib, urllib2
import resources.lib.sdarotcommons as sdarot
from xbmcswift2 import Plugin, xbmc, xbmcgui, ListItem

__plugin__ = "Sdarot.TV Video"
__author__ = "Shai & Roey"

plugin = Plugin()

HEADERS = sdarot.HEADERS
FANART = plugin.addon.getAddonInfo('fanart')
ICON = plugin.addon.getAddonInfo('icon')
API = sdarot.API
POSTER_PREFIX = sdarot.POSTER_PREFIX


@plugin.route('/')
def main_menu():
    items = [
        {
            'label': folder['label'],
            'path': folder['path'],
            'icon': FANART,
            'info': {
                'plot': ' '
            },
            'properties': {
                'Fanart_Image': FANART
            }
        } for folder in [
            {
                'label': u'[COLOR blue] Clean cache - ניקוי מטמון[/COLOR]',
                'path': plugin.url_for('clean')
            },
            {
                'label': u'[COLOR red]Search - חפש[/COLOR]',
                'path': plugin.url_for('search', page=0)
            },
            {
                'label': u'הכל א-ת',
                'path': plugin.url_for('index', lang='heb', page='0')
            },
            {
                'label': u'הכל a-z',
                'path': plugin.url_for('index', lang='eng', page='0')
            },
            {
                'label': u'מועדפים',
                'path': plugin.url_for('favourites')
            },
            {
                'label': u'סדרות מעקב',
                'path': plugin.url_for('tracking_list')
            },
            {
                'label': u'סדרות שלי',
                'path': plugin.url_for('my_shows_list')
            }
        ]
    ]

    req = requests.get(API + '/series/genres').json()

    for genre in req['genres']:
        label = genre['name']
        path = plugin.url_for('open_genre', _id=genre['id'], page=0)
        items.append(sdarot.make_item(label, path, '', FANART, False))

    sdarot.set_dir(items, 504, 'files', plugin)

    sync_storage = plugin.get_storage('sync')
    if not sync_storage.get('vids'):
        sync_storage['vids'] = {}
    return []


@plugin.route('/genre/<_id>/<page>')
def open_genre(_id, page):
    page = int(page)
    req = requests.get(API + '/series/list/{0}/page/{1}/perPage/100'.format(_id, page)).json()

    items = []
    for s in req['series']:
        label = s['heb']
        path = plugin.url_for('open_series', sid=s['id'], title=s['heb'].encode('utf8'))
        items.append(sdarot.make_item(label, path, s['description'], POSTER_PREFIX + s['poster'], False,
                                      fav=build_fav(label, path, s['id'], '0'), year=s['year']))

    if not req['pages']['page'] == req['pages']['totalPages']:
        items.append(sdarot.make_item('[COLOR yellow]{0}[/COLOR]'.format('הבא'),
                                      plugin.url_for('open_genre', _id=_id, page=page + 1), '', FANART, False))

    sdarot.set_dir(items, 504, 'tvshows', plugin)
    return []


@plugin.route('/series/<sid>/<title>')
def open_series(sid, title):
    req = requests.get(API + '/series/info/{0}'.format(sid), headers=HEADERS).json()
    serie = req['serie']

    episodes = serie['episodes']
    if not episodes:
        return []

    items = []
    for season in sorted(episodes.keys(), key=int):
        season_label = u'Season {0}' if eng_only() else u'עונה {0}'
        label = season_label.format(season)
        path = plugin.url_for('open_season', sid=sid, se=season, title=title, title_eng=serie['eng'].encode('utf8'))
        items.append(sdarot.make_item(label, path, serie['description'], POSTER_PREFIX + sid + '.jpg', False,
                                      fav=build_fav(label, path, sid, '0'), genres=req['genres']))

    sdarot.set_dir(items, 504, 'seasons', plugin)
    return []


@plugin.route('/season/<sid>/<se>/<title>/<title_eng>')
def open_season(sid, se, title, title_eng):
    cookie = sdarot.get_user_cookie()
    req = requests.get(API + '/series/info/{0}'.format(sid), cookies=cookie, headers=HEADERS).json()['serie']

    updated_list = plugin.get_storage('updated_list')
    sync_sdarot_vids = plugin.get_storage('sync').get('vids')
    episodes = req['episodes'][str(se)]
    items = []
    for episode in episodes or []:
        if eng_only():
          label = u'Episode S{0}E{1}'.format(str(se).zfill(2), episode['episode'].zfill(2))
        else:
          label = u'פרק {0}'.format(episode['episode'])
        plot = episode['description'].encode('utf-8') or 'לא זמין'
        path = plugin.url_for('watch', sid=sid, season=se, episode=episode['episode'],
                              title=title, vid='None')
        item = sdarot.make_item(label, path, plot, POSTER_PREFIX + sid + '.jpg', True,
                                sid=sid, episode=episode['episode'], season=se,
                                fav=build_fav(label, path, sid, 1), watched=episode['watched'],
                                updated_list=updated_list, is_user=cookie != {},
                                sync_storage=sync_sdarot_vids)
        item['context_menu'].extend([
            ('בחירת איכות', 'XBMC.Container.Update({0})'.format
                (plugin.url_for('choose_quality', sid=sid, season=se, episode=episode['episode'],
                                title=title, title_eng=title_eng, plot=plot))),
            ('הורד פרק', 'XBMC.Container.Update({0})'.format
                (plugin.url_for('download_vid', sid=sid, season=se, ep=episode['episode'],
                                title=title_eng, quality='None')))])
        items.append(item)

    sdarot.set_dir(items, 504, 'episodes', plugin)
    return []


@plugin.route('/quality/<sid>/<season>/<episode>/<title>/<title_eng>/<plot>')
def choose_quality(sid, season, episode, title, title_eng, plot):
    qualities, cookie = sdarot.get_final_video_and_cookie(sid, season, episode, True)

    items = []
    for q in qualities.keys():
        label = '{0}, עונה {1}, פרק {2}, ({3}p)'.format(title, season, episode, q)
        path = plugin.url_for('watch', sid=sid, season=season, episode=episode, title=title,
                              vid=sdarot.build_final_url(qualities[q], cookie))

        item = sdarot.make_item(label, path, plot, POSTER_PREFIX + sid + '.jpg', True,
                                sid=sid, episode=episode, season=season, fav='')
        item['context_menu'].extend([('הורד פרק', 'XBMC.Container.Update({0})'.format(
            plugin.url_for('download_vid', sid=sid, season=season, ep=episode, title=title_eng, quality=q)))])
        items.append(item)

    sdarot.set_dir(items, 504, 'episodes', plugin)
    return []


@plugin.route('/watch/<sid>/<season>/<episode>/<title>/<vid>')
def watch(sid, season, episode, title, vid):
    if vid == 'None':  # Otherwise request was sent from choose_quality and url already exist
        vid, cookie = sdarot.get_final_video_and_cookie(sid, season, episode)

    if vid:
        item = ListItem(**{
            'label': u'פרק {0}'.format(episode),
            'path': vid,
            'thumbnail': POSTER_PREFIX + sid + '.jpg'
        })

        item.as_xbmc_listitem().setContentLookup(False)
        item.set_property('mimetype', 'video/mp4')
        item.set_property('type', 'movie')
        item.set_info('Video', {
                'Title': title,
                'Genre': u'פרק {0}, עונה {1}'.format(episode, season)
            })

        plugin.set_resolved_url(item)
    else:
        plugin.notify(msg='הייתה בעיה, נסו שוב', title='שגיאה', image=ICON)


@plugin.route('/index/<lang>/<page>')
def index(lang, page):
    page = int(page)
    req = requests.get(API + '/series/list/page/{0}/perPage/100/orderBy/{1}'.format(page, lang)).json()
    items = []

    for s in req['series']:
        label = s[lang]
        path = plugin.url_for('open_series', sid=s['id'], title=s[lang].encode('utf8'))
        items.append(sdarot.make_item(label, path, s['description'], POSTER_PREFIX + s['poster'], False,
                                      fav=build_fav(label, path, s['id'], False),
                                      year=s['year'], genres=s['genres'].encode('utf8') if s.get('genres') else ''))

    buttons = {
        'heb': ['הבא', 'הקודם', 'חזרה לדף הראשי', 'עמוד'],
        'eng': ['Next', 'Previous', 'Back To Main Menu', 'Page']
    }

    if not req['pages']['page'] == req['pages']['totalPages']:

        label = '[COLOR yellow]{0}[/COLOR]'.format(buttons[lang][0])
        path = plugin.url_for('index', lang=lang, page=page + 1)
        item = sdarot.make_item(label, path, '', FANART, False)
        items.append(item)

        label = '[COLOR yellow]{0}[/COLOR]'.format(buttons[lang][2])
        path = plugin.url_for('main_menu')
        item = sdarot.make_item(label, path, '', FANART, False)
        items.append(item)

        label = '[COLOR yellow]------- {0} -------[/COLOR]'.format(buttons[lang][3] + ' ' + str(page + 1))
        path = plugin.url_for('empty')
        item = sdarot.make_item(label, path, '', FANART, False)
        items.insert(0, item)

    plugin.set_content('files')
    plugin.finish(items, view_mode=504)

    xbmc.executebuiltin('Control.setFocus(50, 0)')

    return


@plugin.route('/empty')
def empty():
    pass


@plugin.route('/search/<page>')
def search(page):
    page = int(page)

    search_input = ''
    try:
        search_input = plugin.keyboard('', u'חפש כאן')
    except:
        kb = xbmc.Keyboard('', 'חפש כאן')
        kb.doModal()
        if kb.isConfirmed():
            search_input = kb.getText()

    try:
        if len(search_input) < 2:
            plugin.notify('מילת החיפוש חייבת להכיל לפחות שני תווים', image=ICON)
        else:
            s = requests.Session()
            req = requests.Request(method='GET', url=API, headers=HEADERS)
            prep = req.prepare()
            prep.url = API + '/series/search/{0}/page/{1}/perPage/100'.format(search_input, page)
            req = s.send(prep)

            results = req.json()['series']
            if results:
                items = []
                for s in results:
                    label = show_name(s['eng'], s['heb'])
                    path = plugin.url_for('open_series', sid=s['id'], title=s['heb'].encode('utf8'))
                    items.append(sdarot.make_item(label, path, s['description'], POSTER_PREFIX + s['poster'], False,
                                                  fav=build_fav(label, path, s['id'], '0'), year=s['year']))

                sdarot.set_dir(items, 504, 'files', plugin)
                return []
            else:
                plugin.notify('לא נמצאו תוצאות לחיפוש', image=ICON)
    except:
        pass


@plugin.route('/tracking_list')
def tracking_list():
    cookie = sdarot.get_user_cookie()
    if cookie:
        req = requests.get(API + '/tracking/list', cookies=cookie, headers=HEADERS)
        items = [
            {
                'label': u'{0}-{1}'.format(show_name(s['eng'], s['heb']), show_progress(s['watched'],
                                                                                        s['total'])),
                'path': plugin.url_for('open_series', sid=s['serieID'], title=s['heb'].encode('utf8')),
                'icon': POSTER_PREFIX + s['poster'],
                'thumbnail': POSTER_PREFIX + s['poster'],
                'properties': {
                    'Fanart_Image': FANART
                },
                'context_menu': [('הסרה ממעקב',
                                  'XBMC.Container.Update({0})'.format(plugin.url_for('delete_tracking',
                                                                                     sid=s['serieID'],
                                                                                     cookie=cookie['Sdarot'])))]
            } for s in req.json()['list']
        ]
        sdarot.set_dir(items, 504, 'episodes', plugin)
        return []
    else:
        plugin.notify('התחבר כדי להכנס לרשימת מעקב', image=ICON)


def show_name(eng_name, heb_name):
  if eng_only():
    return eng_name
  if heb_only():
    return heb_name
  return u'{0}-{1}'.format(heb_name, eng_name)


def show_progress(watched, total):
  if eng_only():
    return u'Watched {0} of {1} episodes'.format(watched, total)
  if heb_only():
    return  u'צפית ב {0} מתוך {1} פרקים'.format(watched, total)
  return u'צפית ב {0} מתוך {1} פרקים'.format(watched, total)


@plugin.route('/my_shows_list')
def my_shows_list():
    cookie = sdarot.get_user_cookie()
    if cookie:
        req = requests.get(API + '/tracking/list', cookies=cookie, headers=HEADERS)
        items = [
            {
                'label': show_name(s['eng'], s['heb']),
                'path': plugin.url_for('open_series', sid=s['serieID'], title=s['heb'].encode('utf8')),
                'icon': POSTER_PREFIX + s['poster'],
                'thumbnail': POSTER_PREFIX + s['poster'],
                'properties': {
                    'Fanart_Image': FANART
                },
                'context_menu': [('הסרה ממעקב',
                                  'XBMC.Container.Update({0})'.format(plugin.url_for('delete_tracking',
                                                                                     sid=s['serieID'],
                                                                                     cookie=cookie['Sdarot'])))]
            } for s in req.json()['list']
        ]
        sdarot.set_dir(items, 504, 'tvshows', plugin)
        return []
    else:
        plugin.notify('התחבר כדי להכנס לרשימת מעקב', image=ICON)


@plugin.route('/delete_tracking/<sid>/<cookie>')
def delete_tracking(sid, cookie):
    req = requests.get(API + '/tracking/delete/sid/{0}'.format(sid), cookies={'Sdarot': cookie}, headers=HEADERS)
    if req.json()['success']:
        xbmc.executebuiltin('Container.Refresh')
        plugin.notify('סדרה הוסרה!')
    pass


@plugin.route('/clean')
def clean():
    dirs = ['_cache', 'sync', 'index']
    for d in dirs:
        plugin.get_storage(d).clear()

    plugin.get_storage('sync')['vids'] = {}
    plugin.notify('המטמון נמחק', image=ICON)
    pass


@plugin.route('/favourites')
def favourites():
    favs = plugin.get_storage('favourites')
    items = [
        {
            'label': favs[f]['label'],
            'path': favs[f]['path'],
            'is_playable': True if favs[f]['is_playable'] == '1' else False,
            'icon': favs[f]['poster'],
            'thumbnail': favs[f]['poster'],
            'properties': {
                'Fanart_Image': FANART
            },
            'context_menu': [(
                'הסר ממועדפים סדרות', 'XBMC.Container.Update({0})'.format(plugin.url_for('remove_fav', _id=f))
            )]
        } for f in favs.keys()
    ]

    sdarot.set_dir(items, 504, 'episodes', plugin)
    return []


@plugin.route('/add_fav/<label>/<path>/<sid>/<is_playable>')
def add_fav(label, path, sid, is_playable):
    favs = plugin.get_storage('favourites')
    random_id = str(uuid.uuid4().get_hex().upper()[0:6])
    favs[random_id] = {
        'label': label,
        'path': path,
        'poster': POSTER_PREFIX + sid + '.jpg',
        'is_playable': is_playable
        }
    plugin.notify('{0} נוסף למועדפים!'.format(label), image=ICON)


@plugin.route('/remove_fav/<_id>')
def remove_fav(_id):
    try:
        favs = plugin.get_storage('favourites')
        del favs[_id]
    except KeyError:
        plugin.notify('הייתה בעיה, נסה שוב', image=ICON)

    xbmc.executebuiltin('Container.Refresh')
    pass


@plugin.route('/sync')
def sync_sdarot():
    sync_storage = plugin.get_storage('sync')
    if not sync_storage.get('vids'):
        sync_storage['vids'] = {}

    plugin.notify('סנכרון מתבצע ברקע', image=ICON)
    synced = sdarot.sync_sdarot(sync_storage, plugin.get_storage('updated_list'))
    if synced:
        plugin.notify('סנכרון הושלם', image=ICON)
        xbmc.executebuiltin('Container.Refresh')
    else:
        plugin.notify('הייתה בעיה עם הסנכרון, נסה שוב..', image=ICON)
    pass


@plugin.route('/download/<sid>/<season>/<ep>/<title>/<quality>')
def download_vid(sid, season, ep, title, quality):
    dp = plugin.get_setting('download_path')
    if not dp:
        dp = xbmcgui.Dialog().browse(3, 'בחר תיקיית הורדות', 'files', '', False, False, '')
        if not dp:
            plugin.notify('אנא בחרו יעד להורדת הפרק', image=ICON)
            return
    plugin.set_setting('download_path', dp)

    plugin.notify('מכין הורדה..', image=ICON)
    qualities, cookie = sdarot.get_final_video_and_cookie(sid, season, ep, choose_quality=True, download=True)

    if quality == 'None':
        q_dialog = xbmcgui.Dialog()
        q_list = list(qualities.keys())
        q_index = q_dialog.select('בחר איכות', q_list)
        if q_index == -1:
            return
        quality = q_list[q_index]
    url = qualities[quality]
    if url and cookie:
        url = sdarot.get_ip_url(url)
        def download():
            with open(dp + '{0}.S{1}.E{2}_{3}.mp4'.format(title.replace(' ', '.').replace('/', '-'), season, ep, quality + 'P'), 'wb') as f:
                download_headers = {  # Required for download speed
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'User-Agent': HEADERS['User-Agent']
                    ,'Cookie': 'Sdarot={0}'.format(cookie.get('Sdarot'), safe='')
                }

                request = urllib2.Request('http:' + url, headers=download_headers)
                response = urllib2.urlopen(request)
                total_size = response.info().get('Content-Length')

                plugin.notify('ההורדה החלה', image=ICON)

                dialog = xbmcgui.DialogProgressBG()
                dialog.create(f.name)
                dialog.update(1)
                dl = 0

                while True:
                    chunk = response.read(1024 * 30)
                    if not chunk:
                        break
                    dl += len(chunk)
                    dialog.update(100 * dl / int(total_size))
                    f.write(chunk)

                dialog.close()
                response.close()

            plugin.notify('{0} עונה {1} פרק {2} ירד בהצלחה!'.format(title, season, ep), delay=8000, image=ICON)
            return True

        thr = threading.Thread(target=download)
        thr.start()


def build_fav(label, path, sid, is_playable):
    return plugin.url_for('add_fav', label=label.encode('utf-8'), path=path, sid=sid, is_playable=is_playable)


def eng_only():
  is_eng = (xbmc.getLanguage(xbmc.ISO_639_2) == 'eng')
  if not is_eng:
    return False
  return (plugin.get_setting('use_native_lang') == 'true')


def heb_only():
  is_heb = (xbmc.getLanguage(xbmc.ISO_639_2) == 'heb')
  if not is_heb:
    return False
  return (plugin.get_setting('use_native_lang') == 'true')


if __name__ == '__main__':
    try:
        plugin.run()
    except:
        import sys, traceback
        ex_type, ex, tb = sys.exc_info()
        plugin.log.error(ex_type)
        plugin.log.error(ex)
        traceback.print_tb(tb)
        del tb
