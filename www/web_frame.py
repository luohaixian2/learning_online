#!/usr/bin/env python3
#-*- coding: utf-8 -*-

import asyncio, os, inspect, logging, functools

from urllib import parse

from aiohttp import web

from apis import APIError

def get(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			print('get:wrapper was called')
			return func(*args, **kw)
		wrapper.__route__ = path
		wrapper.__method__ = 'GET'
		print('get:decorator return wrapper')
		return wrapper
	print('get:get return decorator')
	return decorator
 
def post(path):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args, **kw):
			print('post:wrapper was called')
			return func(*args, **kw)
		wrapper.__route__ = path
		wrapper.__method__ = 'POST'
		print('post:decorator return wrapper')
		return wrapper
	print('post:get return decorator')
	return decorator

def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

class RequestHandler(object):

	def __init__(self, app, fn):
		self.app = app
		self._func = fn
		print('RequestHandler init called: ', type(fn))
		self._has_request_arg = has_request_arg(fn)
		self._has_var_kw_arg = has_var_kw_arg(fn)
		self._has_named_kw_arg = has_named_kw_args(fn)
		self._named_kw_args = get_named_kw_args(fn)
		self._required_kw_args = get_required_kw_args(fn)
		logging.info('Request all kind of args: _has_request_arg:%s  _has_var_kw_arg: %s  _has_named_kw_arg: %s _named_kw_args: %s   _required_kw_args: %s' % (self._has_request_arg, self._has_var_kw_arg, self._has_named_kw_arg,
		 self._named_kw_args, self._required_kw_args))

	@asyncio.coroutine
	def __call__(self, request):
		logging.info('RequestHandler was called')
		kw = None
		if self._has_request_arg or self._has_var_kw_arg or self._has_named_kw_arg:
			if request.method == 'POST':
				if not request.content_type:
					return web.HTTPBadRequest('Missing content_type')
				ct = request.content_type.lower()
				if ct.startswith('application/json'):
					params = yield from request.json()
					if not isinstance(params, dict):
						return HTTPBadRequest('json body must be a dict object')
					kw = params
				elif ct.startswith('application/x-www-form-urlencode') or ct.startswith('multipart/form-data'):
					params = yield from request.post()
					kw = dict(**params)
				else:
					return HTTPBadRequest('unSupported content_type: %s' % request.content_type)
			if request.method == 'GET':
				qs = request.query_string
				if qs:
					kw = dict()
					for k, v in parse.parse_qs(qs, True).items():
						kw[k] = v[0] #why
		if kw is None:
			kw = dict(**request.match_info)
		else:
			if not self._has_var_kw_arg and self._named_kw_args:
				copy = dict()
				for name in self._named_kw_args:
					if name in kw:
						copy[name] = kw[name]
				kw = copy
			for k, v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
				kw[k] = v
		if self._has_request_arg:
			kw['request'] = request
		if self._required_kw_args:
			for name in self._required_kw_args:
				if not name in kw:
					return web.HTTPBasRequest('Missing argument: %s' % name)
		logging.info('call with args: %s' % str(kw))
		#logging.info('next step func is %s' % str(self._func()))
		try:
			r = yield from self._func(**kw)
			return r
		except APIError as e:
			return dict(error=e.error, data=e.data, message=e.message)
					
def add_static(app):
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
	app.router.add_static('/static/', path)
	logging.info('add static %s => %s' % ('/static/', path))

def add_route(app, fn):
	method = getattr(fn, '__method__', None)
	path = getattr(fn, '__route__', None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in this func: %s' % str(fn))
	if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
		fn = asyncio.coroutine(fn)
	logging.info('add route %s %s => %s (%s)' % (
        method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
	#fn就是匹配到的那个函数
	app.router.add_route(method, path, RequestHandler(app, fn))

def add_routes(app, moudle_name):
	n = moudle_name.rfind('.')
	if n == -1:
		mod = __import__(moudle_name, globals(), locals())
	else:
		name = moudle_name[n+1:]
		mod = getattr(__import__(moudle[:n], globals(), locals(), [name]), name)
	for attr in dir(mod):
		if attr.startswith('_'):
			continue
		fn = getattr(mod, attr)
		if callable(fn):
			method = getattr(fn, '__method__', None)
			path = getattr(fn, '__route__', None)
			if method and path:
				add_route(app, fn)
	
