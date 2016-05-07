#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import logging

import asyncio, os, json, time

from datetime import datetime

from aiohttp import web
from jinja2 import Environment, FileSystemLoader

import orm
from web_frame import add_routes, add_static

from handlers import cookie2user, COOKIE_NAME

logging.basicConfig(level = logging.INFO)

def init_jinja2(app, **kw):
	logging.info('init the jinjia2')
	options = dict(
	autoescape = kw.get('autoescape', True),
	block_start_string = kw.get('block_start_string', '{%'),
	block_end_string = kw.get('block_end_string', '%}'),
	variable_start_string = kw.get('variable_start_string', '{{'),
	variable_end_string = kw.get('variable_end_string', '}}'),
	auto_reload = kw.get('auto_reload', True)
	)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 template path: %s' % path)
	env = Environment(loader = FileSystemLoader(path), **options)
	filters = kw.get('filters', None)
	if filters is not None:
		for name, f in filters.items():
			print('filters: name: %s, f: %s' % (name, f))
			env.filters[name] = f #这里datetime对应datetime_filter这个函数，到时可以在页面引用datetime,就相当于调用这个函数
	app['__templating__'] =  env

@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        logging.info('Request: %s, %s, %s' % (str(request), request.method, request.path))
        # await asyncio.sleep(0.3)
        return (yield from handler(request))
    return logger

@asyncio.coroutine
def data_factory(app, handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = yield from request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (yield from handler(request))
    return parse_data

@asyncio.coroutine
def auth_factory(app, handler):
    @asyncio.coroutine
    def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None
        request.__guide__ = None
        request.__guide_text__ = None
        request.__guide_cur__ = None
        guide = ('personal_video_manage', 'personal_video_owe', 'personal_video_collection', 'personal_study_plane', 'personal_message')
        guide_text = {}
        guide_text['personal_video_manage'] = '教程管理'
        guide_text['personal_video_owe'] = '拥有教程'
        guide_text['personal_video_collection'] = '教程收藏'
        guide_text['personal_study_plane'] = '学习计划'
        guide_text['personal_message'] = '我的消息'
		
        cookie_str = request.cookies.get(COOKIE_NAME)
        if cookie_str:
            user = yield from cookie2user(cookie_str)
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user
                if request.path.startswith('/personal_'):
                    request.__guide__ = guide
                    request.__guide_text__ = guide_text
                    temp_cur_guide = request.path[request.path.find('/')+1:request.path.rfind('/')]
                    if temp_cur_guide == 'personal_video_create':
                        temp_cur_guide = 'personal_video_manage'
                    elif temp_cur_guide == 'personal_study_plane' or temp_cur_guide == 'personal_study_plane_create' or temp_cur_guide == 'personal_study_plane_history':
                        temp_cur_guide = 'personal_study_plane'
                    request.__guide__ = guide
                    request.__guide_cur__ = temp_cur_guide
                    
        #if request.path.startswith('/manage/') and (request.__user__ is None or not request.__user__.admin):
        #    return web.HTTPFound('/signin')
        return (yield from handler(request))
    return auth

@asyncio.coroutine
def response_factory(app, handler):
    @asyncio.coroutine
    def response(request):
        logging.info('Response handler...')
        r = yield from handler(request)
        logging.info('Response comeback...')
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            r['__user__'] = request.__user__
            r['__guide__'] = request.__guide__
            r['__guide_text__'] = request.__guide_text__
            r['__guide_cur__'] = request.__guide_cur__
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(t, str(m))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

def datetime_filter(t):
    delta = (int)(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

@asyncio.coroutine
def init(loop):
    yield from orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='root', password='LHX4878015', db='online_learning')
    app = web.Application(loop=loop, middlewares=[
        logger_factory, auth_factory, response_factory
    ])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'handlers')
    add_static(app)
    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9100)
    logging.info('server started at http://127.0.0.1:9100...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
