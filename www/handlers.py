#!/usr/bin/env
#-*-coding: utf-8-*-

import re, time, json, logging, hashlib, base64, asyncio

from web_frame import get, post

from models import User, Video, Video_type_table, Sub_type, Having_video, Collection_video, Study_plane, Message, Advice, Sub_video, Video_comment, next_id

from aiohttp import web

from apis import APIValueError, APIError, APIPermissionError, Page

from config import configs

import markdown2

import os

import io

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
    free_videos = yield from Video.findAll(where="price=0", orderBy='created_at desc', limit=(4))
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

@get('/lesson/{video_type},{sub_video_type},{page}')
def lesson(*, video_type, sub_video_type, page):
	return {
		'__template__' : 'lesson.html',
		'video_type' : video_type,
		'sub_video_type' : sub_video_type,
		'page_index' : page
	}

def get_page_index(page_str):
    p = 1
    try:
        p = int(page_str)
    except ValueError as e:
        pass
    if p < 1:
        p = 1
    return p

@get('/api/lesson')
def api_get_lesson(*, video_type, sub_video_type, page='1'):
	page_index = get_page_index(page)
	#获取条数	
	if video_type == 'all':
		num = yield from Video.findNumber('count(*)')
	elif sub_video_type.endswith('_all'):
		num = yield from Video.findNumber('count(*)', where="video_type='"+video_type+"'")
	else:
		num = yield from Video.findNumber('count(*)', where="sub_video_type='"+sub_video_type+"'")
	#得到分页的相关信息，比如查询位移
	p = Page(num, page_index, 9)
	if video_type == 'all':
		videos = yield from Video.findAll(orderBy='created_at desc', limit=(p.offset, p.limit))
	elif sub_video_type.endswith('_all'):
		videos = yield from Video.findAll(where="video_type='"+video_type+"'", orderBy='created_at desc', limit=(p.offset, p.limit))
	else:
		videos = yield from Video.findAll(where="sub_video_type='"+sub_video_type+"'", 
		orderBy='created_at desc', limit=(p.offset, p.limit))
	all_video_type = yield from Video_type_table.findAll()
	all_sub_type = {}
	for big_type in all_video_type:
		sub_type = yield from Sub_type.findAll(where="video_type='"+big_type.video_type+"'")
		all_sub_type[big_type.video_type] = sub_type
	return dict(videos=videos, video_type=video_type, sub_video_type=sub_video_type, all_video_type=all_video_type, 
		    all_sub_type = all_sub_type, page = p)

@get('/api/manage_videos')
def api_user_manage_videos(*, page='1', user_id):
	page_index = get_page_index(page)
	num = yield from Video.findNumber('count(*)', where="user_id='"+user_id+"'")
	p = Page(num, page_index, 10)
	videos = yield from Video.findAll(where="user_id='"+user_id+"'", orderBy="created_at desc", limit=(p.offset, p.limit))
	return dict(videos=videos, page = p)

@get('/personal_video_manage/{page}')
def personal_video_manage(*, page='1'):
	return {
		'__template__' : 'personal_video_manage.html',
		'page_index' : page
	}

@get('/personal_video_create/1')
def personal_video_create():
	return {
		'__template__' : 'personal_video_create.html'
	}

@get('/personal_video_owe/{page}')
def personal_video_owe(*, page='1'):
	return {
		'__template__' : 'personal_video_owe.html',
		'page_index' : page
	}

@get('/personal_video_collection/{page}')
def personal_video_collection(*, page='1'):
	return {
		'__template__' : 'personal_video_collection.html',
		'page_index' : page
	}

@get('/personal_study_plane/{page}')
def personal_study_plane(*, page='1'):
	return {
		'__template__' : 'personal_study_plane.html',
		'page_index' : page
	}

@get('/personal_message/{page}')
def personal_message(*, page='1'):
	return {
		'__template__' : 'personal_message.html',
		'page_index' : page
	}

@get('/personal_study_plane_history/{page}')
def personal_study_plane_history(*, page='1'):
	return {
		'__template__' : 'personal_study_plane_history.html',
		'page_index' : page
	}

@get('/personal_study_plane_create/1')
def personal_study_plane_create():
        return {
                '__template__' : 'personal_study_plane_edit.html',
                'id' : '',
                'action' : '/personal_post_study_plane_create'
        }

@get('/personal_study_plane_view/{id}')
def personal_study_plane_view(*, id):
        return {
                '__template__' : 'personal_study_plane_view.html',
                'id' : id
        }

@get('/personal_message_view/{id}')
def personal_message_view(*, id):
        message = yield from Message.find(id)
        return {
                '__template__' : 'personal_message_view.html',
                'message' : message
        }

@get('/personal_sub_video_view/{sub_video_id}')
def personal_sub_video_view(*, sub_video_id):
        sub_video = yield from Sub_video.find(sub_video_id)
        video = yield from Video.find(sub_video.parent_video_id)
        return {
                '__template__' : 'personal_sub_video_view.html',
                'parent_video_name' : video.name,
                'sub_video' : sub_video
        }

@get('/personal_study_plane_edit/{id}')
def personal_study_plane_edit(*, id):
        return {
                '__template__' : 'personal_study_plane_edit.html',
                'id' : id,
                'action' : '/personal_post_study_plane_edit/%s' % id
        }

@get('/personal_video_edit/{video_id},{page}')
def personal_video_edit(*, video_id, page='1'):
        return {
                '__template__' : 'personal_video_edit.html',
                'parent_video_id' : video_id,
		'page_index' : page
        }

@get('/manage_user/{page}')
def manage_user(*, page='1'):
        return {
                '__template__' : 'manage_user.html',
                'page_index' : page
        }

@get('/manage_advice/{page}')
def manage_advice(*, page='1'):
        return {
                '__template__' : 'manage_advice.html',
                'page_index' : page
        }

@get('/manage_video/{page}')
def manage_video(*, page='1'):
        return {
                '__template__' : 'manage_video.html',
                'page_index' : page
        }

@get('/personal_get_video_create')
def personal_get_video_create():
	all_video_type = yield from Video_type_table.findAll()
	all_sub_type = {}
	for big_type in all_video_type:
		sub_type = yield from Sub_type.findAll(where="video_type='"+big_type.video_type+"'")
		all_sub_type[big_type.video_type] = sub_type
	return dict(all_video_type=all_video_type, all_sub_type=all_sub_type)

@get('/personal_get_video_owe')
def personal_get_video_owe(*, user_id, page='1'):
	page_index = get_page_index(page)
	num = yield from Having_video.findNumber('count(*)', where="user_id='"+user_id+"'")
	p = Page(num, page_index, 10)
	results = []
	hav_videos = yield from Having_video.findAll(where="user_id='"+user_id+"'", orderBy="created_at desc", limit=(p.offset, p.limit))
	for hav_video in hav_videos:
		result = {}
		result['created_at'] = hav_video.created_at
		print('TERSREE',hav_video.video_id)
		video = yield from Video.findAll(where="id='"+hav_video.video_id+"'")
		if video is not None:
			result['id'] = video[0].id
			result['name'] = video[0].name
			result['dir_num'] = video[0].dir_num
			result['price'] = video[0].price
			result['video_progress'] = str((hav_video.progress_num-1)/video[0].dir_num*100)+"%"
			results.append(result)
	return dict(videos=results, page = p)
	
@get('/personal_get_video_collection')
def personal_get_video_collection(*, user_id, page='1'):
	page_index = get_page_index(page)
	num = yield from Collection_video.findNumber('count(*)', where="user_id='"+user_id+"'")
	p = Page(num, page_index, 10)
	results = []
	hav_videos = yield from Collection_video.findAll(where="user_id='"+user_id+"'", orderBy="created_at desc", limit=(p.offset, p.limit))
	for hav_video in hav_videos:
		result = {}
		result['created_at'] = hav_video.created_at
		result['id'] = hav_video.id
		video = yield from Video.findAll(where="id='"+hav_video.video_id+"'")
		if video is not None:
			result['video_id'] = video[0].id
			result['name'] = video[0].name
			result['dir_num'] = video[0].dir_num
			result['price'] = video[0].price
			results.append(result)
	return dict(videos=results, page = p)

@get('/personal_get_study_plane')
def personal_get_study_plane(*, user_id, page='1'):
	page_index = get_page_index(page)
	num = yield from Study_plane.findNumber('count(*)', where="user_id='"+user_id+"' and plane_state='ing'")
	p = Page(num, page_index, 1)
	planes = yield from Study_plane.findAll(where="user_id='"+user_id+"' and plane_state='ing'", orderBy="created_at desc", 
	limit=(p.offset, p.limit))
	return dict(planes=planes, page=p)

@get('/personal_get_sub_video')
def personal_get_sub_video(*, parent_video_id, page='1'):
	page_index = get_page_index(page)
	num = yield from Sub_video.findNumber('count(*)', where="parent_video_id='"+parent_video_id+"'")
	p = Page(num, page_index, 1)
	sub_videos = yield from Sub_video.findAll(where="parent_video_id='"+parent_video_id+"'", orderBy="num", 
	limit=(p.offset, p.limit))
	return dict(sub_videos=sub_videos, page=p)

@get('/personal_get_message')
def personal_get_message(*, user_id, page='1'):
	page_index = get_page_index(page)
	num = yield from Message.findNumber('count(*)', where="recv_id='"+user_id+"'")
	p = Page(num, page_index, 1)
	messages = yield from Message.findAll(where="recv_id='"+user_id+"'", orderBy="created_at desc", 
	limit=(p.offset, p.limit))
	return dict(messages=messages, page=p)

@get('/personal_get_study_plane_history')
def personal_get_study_plane_history(*, user_id, page='1'):
	page_index = get_page_index(page)
	num = yield from Study_plane.findNumber('count(*)', where="user_id='"+user_id+"' and plane_state!='ing'")
	p = Page(num, page_index, 10)
	planes = yield from Study_plane.findAll(where="user_id='"+user_id+"' and plane_state!='ing'", orderBy="created_at desc", 
	limit=(p.offset, p.limit))
	return dict(planes=planes, page=p)

@get('/manage_get_user')
def manage_get_user(*, page='1'):
	page_index = get_page_index(page)
	p = Page(num, page_index, 1)
	users = yield from User.findAll(orderBy="created_at desc", limit=(p.offset, p.limit))
	return dict(users=users, page=p)

@get('/manage_get_video')
def manage_get_video(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Video.findNumber('count(*)')
	p = Page(num, page_index, 1)
	videos = yield from Video.findAll(orderBy="created_at desc", limit=(p.offset, p.limit))
	return dict(videos=videos, page=p)

@get('/manage_get_advice')
def manage_get_advice(*, page='1'):
	page_index = get_page_index(page)
	num = yield from Advice.findNumber('count(*)')
	p = Page(num, page_index, 1)
	advices = yield from Advice.findAll(orderBy="created_at desc", limit=(p.offset, p.limit))
	return dict(advices=advices, page=p)

@get('/personal_get_study_plane_edit/{id}')
def personal_get_study_plane_edit(*, id):
    plane = yield from Study_plane.find(id)
    return plane

@get('/personal_get_video/{video_id}')
def personal_get_video(*, video_id):
    video = yield from Video.find(video_id)
    return video

@get('/personal_video_base_edit/{parent_video_id}')
def personal_video_base_edit(*, parent_video_id):
    return {
        '__template__': 'personal_video_base_edit.html',
        'parent_video_id' : parent_video_id
    }

@get('/personal_sub_video_upload/{parent_video_id}')
def personal_sub_video_upload(*, parent_video_id):
    return {
        '__template__': 'personal_sub_video_upload.html',
        'parent_video_id' : parent_video_id
    }

@get('/personal_get_video_edit/{video_id}')
def personal_get_video_edit(*, video_id):
    video = yield from Video.find(video_id)
    all_video_type = yield from Video_type_table.findAll()
    all_sub_type = {}
    for big_type in all_video_type:
        sub_type = yield from Sub_type.findAll(where="video_type='"+big_type.video_type+"'")
        all_sub_type[big_type.video_type] = sub_type
    return {
        'video' : video,
        'all_video_type' : all_video_type,
        'all_sub_type' : all_sub_type
    }

@get('/detail_lesson/{id}')
def get_video(request, *, id):
    video = yield from Video.find(id)
    sub_videos = yield from Sub_video.findAll(where="parent_video_id='"+id+"'", orderBy="num")
    user_video = yield from Having_video.findAll(where="user_id='"+request.__user__.id+"' and video_id='"+id+"'")
    collection_video = yield from Collection_video.findAll(where="user_id='"+request.__user__.id+"' and video_id='"+id+"'")
    comments = None
    is_having = None
    progress = None
    collection_id = None
    num = 0
    if collection_video:
        collection_id = collection_video[0].id
    if user_video:
        is_having = True
        num = user_video[0].progress_num
        progress = str((user_video[0].progress_num-1)/video.dir_num*100)
        comments = yield from Video_comment.findAll(where="video_id='"+user_video[0].id+"'")
    print(collection_id)
    return {
        '__template__': 'detail_lesson.html',
        'video': video,
        'sub_videos' : sub_videos,
        'progress' : progress,
        'is_having' : is_having,
        'comments' : comments,
        'num' : num,
        'collection_id' : collection_id
    }

@get('/video/{id},{num}')
def video(*, id, num):
	sub_video = yield from Sub_video.findAll(where="parent_video_id='"+id+"' and num='"+num+"'");
	if not sub_video:
		return {
			'__template__' : 'video.html',
			'video' : None
		}
	return {
	'__template__' : 'video.html',
	'video' : sub_video[0]
}

@get('/test')
def test():
	return {
		'__template__' : 'test.html'
	}

@get('/personal_file_upload_test')
def personal_file_upload_test():
	return {
	'__template__' : 'personal_file_upload_test.html'
}

@post('/personal_post_file_upload_test')
def personal_post_file_upload_test(request,*,test):
	print("file have been revRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")
	io_file = test.file
	data = io_file.read()
	os.chdir('/home/luohaixian/software/myproject/learning_online/www/templates')
	name = 'eee'
	path = '../static/video/'+request.__user__.email+'/'+name+'/test'
	print(path)
	f = open(path,'wb')
	#while True:
	#	chunk = io_file.read()
	#	if not chunk:
	#		break
	#	f.write(chunk)
	f.write(data)
	f.close()

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

@post('/owe_video/{video_id}')
def owe_video(request, *, video_id):
	having_video =Having_video(user_id=request.__user__.id, video_id=video_id, progress_num=1)
	yield from having_video.save()
	return having_video

@post('/collection_video/{video_id}')
def collection_video(request, *, video_id):
	collection_video =Collection_video(user_id=request.__user__.id, video_id=video_id)
	yield from collection_video.save()
	return collection_video

@post('/cancel_collection_video/{collection_id}')
def cancel_collection_video(*, collection_id):
	collection_video = yield from Collection_video.find(collection_id)
	print(collection_video)
	if collection_video:
		yield from collection_video.remove()
	return dict(collection_id=collection_id)

@post('/personal_collection_video/delete/{id}')
def personal_collection_delete(*, id):
    video = yield from Collection_video.find(id)
    yield from video.remove()
    return dict(id=id)

@post('/manage_user_delete/{id}')
def manage_user_delete(*, id):
    user = yield from User.find(id)
    yield from user.remove()
    return dict(id=id)

@post('/manage_video_delete/{id}')
def manage_video_delete(*, id):
    video = yield from Video.find(id)
    yield from video.remove()
    return dict(id=id)

@post('/manage_advice_delete/{id}')
def manage_advice_delete(*, id):
    advice = yield from Advice.find(id)
    yield from advice.remove()
    return dict(id=id)

@post('/personal_message/delete/{id}')
def personal_collection_delete(*, id):
    message = yield from Message.find(id)
    yield from message.remove()
    return dict(id=id)

@post('/personal_study_plane_delete/{id}')
def personal_study_plane_delete(*, id):
    plane = yield from Study_plane.find(id)
    yield from plane.remove()
    return dict(id=id)

@post('/personal_video_delete/{video_id}')
def personal_video_delete(request, *, video_id):
    video = yield from Video.find(video_id)
    if video:
        yield from video.remove()
    path = '../static/video/'+request.__user__.email+'/'+video_id+'/'
    os.chdir('/home/luohaixian/software/myproject/learning_online/www/templates')
    os.system('rm -r '+path)
    return dict(video_id=video_id)

@post('/personal_sub_video_delete/{sub_video_id}')
def personal_sub_video_delete(request, *, sub_video_id):
    sub_video = yield from Sub_video.find(sub_video_id)
    path = '../static/video/'+request.__user__.email+'/'+sub_video.parent_video_id+'/'+str(sub_video.num)+'.mp4'
    print(path)
    if sub_video:
        yield from sub_video.remove()
    os.chdir('/home/luohaixian/software/myproject/learning_online/www/templates')
    os.system('rm '+path)
    return dict(sub_video_id=sub_video_id)

@post('/personal_post_study_plane_create')
def personal_post_study_plane_create(request, *, plane_title, plane_content, start_time, end_time):
    #检查是否是管理员操作，用user中的admin属性
    #check_admin(request)
    if not plane_title or not plane_title.strip():
        raise APIValueError('title', 'title cannot be empty.')
    if not plane_content or not plane_content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    if not start_time or not start_time.strip():
        raise APIValueError('start_time', 'start_time cannot be empty.')
    plane = Study_plane(user_id=request.__user__.id, plane_title=plane_title.strip(), plane_content=plane_content.strip(), plane_state='ing', start_time=start_time.strip(), end_time=end_time.strip())
    yield from plane.save()
    return plane

@post('/personal_post_video_create')
def personal_post_video_create(request, *, name, video_type, sub_video_type, price, dir_num, describe):
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not video_type or not video_type.strip():
        raise APIValueError('video_type', 'video_type cannot be empty.')
    if not sub_video_type or not sub_video_type.strip():
        raise APIValueError('sub_video_type', 'sub_video_type cannot be empty.')
    if not describe or not describe.strip():
        raise APIValueError('describe', 'describe cannot be empty.')
    video = Video(name=name.strip(), video_type=video_type.strip(), sub_video_type=sub_video_type.strip(), pic_path='null', user_name=request.__user__.name, describe=describe.strip(), user_id=request.__user__.id, price=price, dir_num=dir_num, people_num=0)
    yield from video.save()
    #these code is not strong,should be use subprocess
    path = '../static/video/'+request.__user__.email+'/'+video.id+'/'
    pic_path = path + 'video_pic'
    video.pic_path = pic_path
    yield from video.update()
    os.chdir('/home/luohaixian/software/myproject/learning_online/www/templates')
    os.system('mkdir '+path)
    os.system('cp ../static/src/test.png '+pic_path)
    return video

@post('/personal_post_study_plane_edit/{id}')
def personal_post_study_plane_edit(id, request, *, plane_title, plane_content, start_time, end_time):
    #check_admin(request)
    plane = yield from Study_plane.find(id)
    if not plane_title or not plane_title.strip():
        raise APIValueError('title', 'title cannot be empty.')
    if not plane_content or not plane_content.strip():
        raise APIValueError('content', 'content cannot be empty.')
    if not start_time:
        raise APIValueError('start_time', 'start_time cannot be empty.')
    if not end_time:
        raise APIValueError('end_time', 'end_time cannot be empty.')
    plane.plane_title = plane_title.strip()
    plane.plane_content = plane_content.strip()
    plane.start_time = start_time
    plane.end_time = end_time
    yield from plane.update()
    return plane

@post('/personal_post_video_edit/{id}')
def personal_post_study_plane_edit(id, request, *, name, video_type, sub_video_type, price, dir_num, describe):
    #check_admin(request)
    video = yield from Video.find(id)
    if not name or not name.strip():
        raise APIValueError('name', 'name cannot be empty.')
    if not video_type or not video_type.strip():
        raise APIValueError('video_type', 'video_type cannot be empty.')
    if not sub_video_type or not sub_video_type.strip():
        raise APIValueError('sub_video_type', 'sub_video_type cannot be empty.')
    if not describe or not describe.strip():
        raise APIValueError('video_type', 'video_type cannot be empty.')
    if not price:
        raise APIValueError('price', 'price cannot be empty.')
    if not dir_num:
        raise APIValueError('dir_num', 'dir_num cannot be empty.')
    video.name = name.strip()
    video.video_type = video_type.strip()
    video.sub_video_type = sub_video_type
    video.price = price
    video.dir_num = dir_num
    video.describe = describe
    yield from video.update()
    return video

@post('/personal_post_pic_upload/{video_id}')
def personal_post_pic_upload(request,*,video_id,test):
	print("file have been revRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRRR")
	print(video_id)
	io_file = test.file
	data = io_file.read()
	os.chdir('/home/luohaixian/software/myproject/learning_online/www/templates')
	path = '../static/video/'+request.__user__.email+'/'+video_id+'/video_pic'
	f = open(path,'wb')
	#while True:
	#	chunk = io_file.read()
	#	if not chunk:
	#		break
	#	f.write(chunk)
	f.write(data)
	f.close()
	return {
        	'__template__': 'personal_video_base_edit.html',
        	'parent_video_id' : video_id
	}

@post('/personal_post_sub_video_upload/{video_id}')
def personal_post_sub_video_upload(request,*,video_id,test,num,title):
	print("file have been revRRRRROOOOOOOOOOOOOOOOOOOOOORRRRR")
	print(video_id,title,num,test)
	io_file = test.file
	data = io_file.read()
	os.chdir('/home/luohaixian/software/myproject/learning_online/www/templates')
	path = '../static/video/'+request.__user__.email+'/'+video_id+'/'+num+'.mp4'
	f = open(path,'wb')
	f.write(data)
	f.close()
	if not title or not title.strip():
        	raise APIValueError('title', 'title cannot be empty.')
	if not num:
		raise APIValueError('num', 'num cannot be empty.')
	sub_video = Sub_video(parent_video_id=video_id, title=title.strip(), video_path=path, num=num)
	yield from sub_video.save()
	return {
        	'__template__': 'personal_video_edit.html',
        	'parent_video_id' : video_id
	}
#----------------------------------------------------
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
