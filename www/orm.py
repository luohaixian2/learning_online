
#-*- coding: utf-8 -*-

import asyncio, logging

import aiomysql

def log(sql, args = ()):
	print('sql:%s, args:%s' % (sql, args))

@asyncio.coroutine
def create_pool(loop, **kw):
	logging.info('create database connection pool...')
	global __pool
	__pool = yield from aiomysql.create_pool(
		host = kw.get('host', 'localhost'),
		port = kw.get('port', 3306),
		user = kw['user'],
		password = kw['password'],
		db = kw['db'],
		charset = kw.get('charset', 'utf8'),
		autocommit = kw.get('autocommit', True),
		maxsize = kw.get('maxsize', 10),
		minsize = kw.get('minsize', 1),
		loop = loop
	)

@asyncio.coroutine
def select(sql, args, size = None):
	log(sql, args)
	with (yield from __pool) as conn:
		cur = yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?', '%s'), args or ())
		if size:
			rs = yield from cur.fetchmany(size)
		else:
			rs = yield from cur.fetchall()
	logging.info('get %s rows' % len(rs))
	return rs

@asyncio.coroutine
def execute(sql, args, autocommit = True):
	log(sql, args)
	with (yield from __pool) as conn:
		if not autocommit:
			yield from conn.begin() #why
		try:
			cur = yield from conn.cursor()
			yield from cur.execute(sql.replace('?', '%s'), args)
			affected_row = cur.rowcount
			yield from cur.close()
			if not autocommit:
				yield from conn.commit()
		except BaseException as e:
			if not autocommit:
				yield from conn.rollback()
			raise e
	return affected_row

#def special_select_owe_method(sql):
	

class Field(object):
	def __init__(self, name, column_type, primary_key, default):
		self.name = name
		self.column_type = column_type
		self.primary_key = primary_key
		self.default = default

	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):
	def __init__(self, name = None, primary_key = False, default = None, ddl = 'varchar(100)'):
		super().__init__(name, ddl, primary_key, default)

	def __str__(self):
		return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

def create_args_string(size):
	l = []
	for i in range(size):
		l.append('?')
	return ', '.join(l)

class ModelMetaclass(type):
	def __new__(cls, name, bases, attrs):
		if name == 'Model':
			return type.__new__(cls, name, bases, attrs)
		tableName = attrs.get('__table__', None) or name
		mappings = dict()
		fields = []
		primary_key = None
		for k, v in attrs.items():
			if isinstance(v, Field):
				mappings[k] = v
				if v.primary_key:
					if primary_key:
						raise RuntimeError('Dumplicate primary key field %s' % k)
					primary_key = k
				else:
					fields.append(k)
		if not primary_key:
			raise RuntimeError('No primary key found')
		for k in mappings.keys():
			attrs.pop(k)
		escaped_fields = list(map(lambda f: '`%s`' %f, fields))
		attrs['__table__'] = tableName
		attrs['__mappings__'] = mappings
		attrs['__primary_key__'] = primary_key
		attrs['__fields__'] = fields
		#why should add ``
		attrs['__select__'] = 'select `%s`, %s from `%s`' % (primary_key, ','.join(escaped_fields), tableName)
		attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(
            	escaped_fields), primary_key, create_args_string(len(escaped_fields) + 1))
		attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primary_key)
		attrs['__delete__'] = 'delete from `%s` where `%s` = ?' % (tableName, primary_key)
		return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass = ModelMetaclass):
	def __init__(self, **kw):
		super(Model, self).__init__(**kw)
	
	def __getattr__(self, k):
		try:
			return self[k]
		except KeyError:
			raise AttributeError(r'Model object has no the attribute %s' % k)

	def __setattr__(self, k, v):
		self[k] = v

	def getValue(self, k):
		return getattr(self, k, None)

	def getValueOrDefault(self, key):
		value = getattr(self, key, None)
		if value is None:
			field = self.__mappings__[key]
			if field.default is not None:
				value = field.default() if callable(field.default) else field.default
				setattr(self, key, value)
		return value
	@classmethod
	@asyncio.coroutine
	def findAll(cls, where = None, args = None, **kw):
		sql = [cls.__select__]
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args = []
		orderBy = kw.get('orderBy', None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit = kw.get('limit', None)
		if limit:
			sql.append('limit')
			if isinstance(limit, int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit, tuple) and len(limit) == 2:
				sql.append('?, ?')
				args.extend(limit)
			else:
				raise ValueError('InValid limit value: %s' % str(limit))
		rs = yield from select(' '.join(sql), args)
		return [cls(**r) for r in rs] #why is cls(**r)

	@classmethod
	@asyncio.coroutine
	def findNumber(cls, selectField, where = None, args = None):
		sql = ['select %s _num_ from `%s` ' % (selectField, cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs = yield from select(' '.join(sql), args, 1)
		if len(rs) == 0:
			return None
		return rs[0]['_num_'] #why

	@classmethod
	@asyncio.coroutine
	def find(cls, pk):
		'find object by primary key [pk] is like args'
		rs = yield from select('%s where `%s` = ?' % (cls.__select__, cls.__primary_key__), [pk], 1)
		if len(rs) == 0:
			return None
		return cls(**rs[0])

	@asyncio.coroutine
	def save(self):
		args = list(map(self.getValueOrDefault, self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows = yield from execute(self.__insert__, args)
		if rows != 1:
			print('failed to insert')
	
	@asyncio.coroutine
	def update(self):
		args = list(map(self.getValue, self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		print('%s -- %s' %(self.__update__, args))
		#不止一次因为这个yield from而报错
		rows = yield from execute(self.__update__, args)
		if rows != 1:
			print('update failed')
	
	@asyncio.coroutine
	def remove(self):
		args = [self.getValue(self.__primary_key__)]
		rows = yield from execute(self.__delete__, args)
		if rows != 1:
			print('failed delete ')
	
