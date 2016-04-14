#!/usr/bin/env
#-*-coding: utf-8-*-

import re, time, json, logging, hashlib, base64, asyncio

from web_frame import get, post

from models import User, Video, next_id

from aiohttp import web

from apis import APIValueError, APIError, APIPermissionError, Page

from config import configs

import markdown2

COOKIE_NAME = 'awesession'
_COOKIE_KEY = configs.session.secret

_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')

def user2cookie(user, max_age):
	expires = str(int(time.time()) + max_age)
	s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
	L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)
	
@asyncio.coroutine
def cookie2user(cookie_str):
	if not cookie_str:
		return None
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		id, expires, sha1 = L
		if int(expires) < time.time():
			return None
		user = yield from User.find(id)
		if user is None:
			return None
		s = '%s-%s-%s-%s' % (user.id, user.passwd, expires, _COOKIE_KEY)
		if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.passwd = '*****'
		return user
	except Exception as e:
		logging.exception(e)
		return None

# 把存文本文件转为html格式的文本
def text2html(text):
    lines = map(lambda s: '<p>%s</p>' % s.replace('&', '&amp;').replace('<',
    '&lt;').replace('>', '&gt;'), filter(lambda s: s.strip() != '', text.split('\n')))
    return ''.join(lines)

#-----get方法-----#
@get('/')
def index():
	return {
	'__template__' : 'home.html'
	}

@get('/api/videos')
def api_videos():
    free_videos = yield from Video.findAll(where="video_type='free'", orderBy='created_at desc', limit=(4))
    it_videos = yield from Video.findAll(where="video_type='it'", orderBy='created_at desc', limit=(4))
    work_skill_videos = yield from Video.findAll(where="video_type='work_skill'", orderBy='created_at desc', limit=(4))
    language_videos = yield from Video.findAll(where="video_type='language'", orderBy='created_at desc', limit=(4))
    hobby_videos = yield from Video.findAll(where="video_type='hobby'", orderBy='created_at desc', limit=(4))
    return dict(free_videos=free_videos, it_videos=it_videos, work_skill_videos=work_skill_videos, language_videos=language_videos,
    hobby_videos=hobby_videos)

@get('/register')
def register():
        return {
                '__template__' : 'register.html'
        }

@get('/signin')
def signin():
        return {
                '__template__' : 'signin.html'
        }

@get('/signout')
def signout(request):
        referer = request.headers.get('Referer')
        r = web.HTTPFound(referer or '/')
        r.set_cookie(COOKIE_NAME, '-deleted-', max_age = 0, httponly = True)
        logging.info('user sign out.')
        return r

@get('/personal')
def personal():
	return {
		'__template__' : 'personal.html'
	}

@get('/mystorm')
def mystorm():
	return {
		'__template__' : 'mystorm.html'
	}

@get('/stuplane')
def stuplane():
	return {
		'__template__' : 'stuplane.html'
	}

@get('/mylove')
def mylove():
	return {
		'__template__' : 'mylove.html'
	}

@get('/mydiscuss')
def mydiscuss():
	return {
		'__template__' : 'mydiscuss.html'
	}

@get('/lesson/{video_type},{sub_video_type}')
def lesson(*, video_type, sub_video_type):
	return {
		'__template__' : 'lesson.html',
		'video_type' : video_type,
		'sub_video_type' : sub_video_type
	}

@get('/api/lesson')
def api_get_lesson(*, video_type, sub_video_type, page='1'):
	if video_type == 'all':
		videos = yield from Video.findAll(orderBy='created_at desc')
	elif sub_video_type == 'all':
		videos = yield from Video.findAll(where="video_type=video_type", orderBy='created_at desc')
	else:
		videos = yield from Video.findAll(where="video_type='"+video_type+"' and sub_video_type='"+sub_video_type+"'", orderBy='created_at desc')
	return dict(videos=videos, video_type=video_type, sub_video_type=sub_video_type)

@get('/detail_lesson/{id}')
def get_video(*, id):
    video = yield from Video.find(id)
    return {
        '__template__': 'detail_lesson.html',
        'video': video
    }

@get('/video/{id}')
def video(*, id):
	video = yield from Video.find(id);
	return {
	'__template__' : 'video.html',
	'video' : video
}

@get('/test')
def test():
	return {
		'__template__' : 'test.html'
	}

@get('/manage/blogs/create')
def create_blogs():
	return {
		'__template__' : 'manage_blog_edit.html',
		'id' : '',
		'action' : '/api/blogs'
	}


@get('/manage/blogs/edit')
def edit_blogs(*, id):
	return {
		'__template__' : 'manage_blog_edit.html',
		'id' : id,
		'action' : '/api/blogs/%s' % id
	}

#-----post方法-----#
@post('/api/users')
def api_register_user(*, email, name, passwd):
        print('ready to register')
        if not name or not name.strip():
                raise APIValueError('name')
        if not email or not _RE_EMAIL.match(email):
                raise APIValueError('email')
        if not passwd or not _RE_SHA1.match(passwd):
                raise APIValueError('passwd4')
        users = yield from User.findAll('email = ?', [email])
        if len(users) > 0:
                raise APIError('register failed, this email is already register')
        uid = next_id()
        sha1_passwd = '%s:%s' % (uid, passwd)
        user = User(id = uid, name = name.strip(), email = email, passwd = hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),
        image = 'http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
        yield from user.save()

        r = web.Response()
        r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
        user.passwd = '******'
        r.content_type = 'application/json'
        r.body = json.dumps(user, ensure_ascii = False).encode('utf-8')
        return r


@post('/api/authenticate')
def authenticate(*, email, passwd):
	print('authenticate func was called')
	if not email:
		raise APIValueError('email', 'Invalid email')
	if not passwd:
		raise APIValueError('passwd', 'InValid passwd2')
	users = yield from User.findAll('email = ?', [email])
	if len(users) == 0:
		raise APIValueError('email', 'email not exist')
	user = users[0]
	sha1 = hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.passwd != sha1.hexdigest():
		raise APIValueError('passwd', 'Invalid passwd3')
	r = web.Response()
	r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age = 86400, httponly = True)
	user.passwd = '*****'
	r.content_type = 'application/json'
	r.body = json.dumps(user, ensure_ascii = False).encode('utf-8')
	return r

def check_admin(request):
    #print('Request.__user_: _' , request.__user__)
    if request.__user__ is None or not request.__user__.admin:
        raise APIPermissionError()

@post('/api/blogs')
def api_create_blog(request, *, name, summary, content):
    #检查是否是管理员操作，用user中的admin属性
    #check_admin(request)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog = Blog(user_id=request.__user__.id, user_name=request.__user__.name, user_image=request.__user__.image, name=name.strip(), summary=summary.strip(), content=content.strip())
    yield from blog.save()
    return blog

@post('/api/blogs/{id}')
def api_update_blog(id, request, *, name, summary, content):
    #check_admin(request)
    blog = yield from Blog.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not summary or not summary.strip():
        raise APIValueError('summary', 'summary cannot be empty.')
    if not content or not content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    blog.name = name.strip()
    blog.summary = summary.strip()
    blog.content = content.strip()
    yield from blog.update()
    return blog

@post('/api/blogs/{id}/delete')
def api_delete_blog(request, *, id):
    #check_admin(request)
    blog = yield from Blog.find(id)
    yield from blog.remove()
    return dict(id=id)

@get('/api/blogs/{id}')
def api_get_blog(*, id):
    blog = yield from Blog.find(id)
    return blog

@get('/blogs/{id}')
def get_blog(id):
    blog = yield from Blog.find(id)
    comments = yield from Comment.findAll('blog_id=?', [id], orderBy='created_at desc')
    for c in comments:
        #c.html_content = text2html(c.content)
        c.html_content = c.content
    #blog.html_content = markdown2.markdown(blog.content)
    blog.html_content = blog.content
    return {
        '__template__': 'blog.html',
        'blog': blog,
        'comments': comments
    }

@get('/api/users')
def api_get_users():
	users = yield from User.findAll(orderBy = 'created_at desc') #desc是反向排序
	for u in users:
		u.passwd = '99999'
	return dict(users = users)

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

@get('/api/blogs')
def api_blogs(*, page='1'):
    page_index = get_page_index(page)
    num = yield from Blog.findNumber('count(id)')
    p = Page(num, page_index)
    if num == 0:
        return dict(page=p, blogs=())
    blogs = yield from Blog.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
    return dict(page=p, blogs=blogs)

@get('/manage/blogs')
def manage_blogs(*, page='1'):
    return {
        '__template__': 'manage_blogs.html',
        'page_index': get_page_index(page)
    }

@post('/api/blogs/{id}/comments')
def create_comment(id, request, *, content):
	user = request.__user__
	if user is None:
		raise APIPermissionError('content')
	if not content or not content.strip():
		raise APIValueError('content')
	blog = yield from Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('blog')
	comment = Comment(blog_id = blog.id, user_id = user.id, user_name = user.name, user_image = user.image, content = content.strip())
	yield from comment.save()
	return comment
