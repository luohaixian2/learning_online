import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

class Video(Model):
    __table__ = 'videos'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    name = StringField(ddl='varchar(50)')
    video_type = StringField(ddl='varchar(20)')
    sub_video_type = StringField(ddl='varchar(20)')
    pic_path = StringField(ddl='varchar(300)')
    video_path = StringField(ddl='varchar(300)')
    describe = StringField(ddl='varchar(200)')
    user_id = StringField(ddl='varchar(50)')
    price = FloatField()
    dir_num = StringField(ddl='int')
    people_num = StringField(ddl='int')
    created_at = FloatField(default=time.time)

class Video_type_table(Model):
	__table__ = 'video_type_table'

	video_type = StringField(primary_key=True, ddl='varchar(20)')
	video_type_text = StringField(ddl='varchar(20)')

class Sub_type(Model):
	__table__ = 'sub_type'

	video_type = StringField(ddl='varchar(20)')
	sub_video_type = StringField(primary_key=True, ddl='varchar(20)')
	sub_video_type_text = StringField(ddl='varchar(20)')

class Having_video(Model):
	__table__ = 'having_videos'
	
	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	video_id = StringField(ddl='varchar(50)')
	video_progress = StringField(ddl='varchar(20)')
	created_at = FloatField(default=time.time)

class Collection_video(Model):
	__table__ = 'collection_videos'
	
	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	video_id = StringField(ddl='varchar(50)')
	created_at = FloatField(default=time.time)

class Study_plane(Model):
	__table__ = 'study_planes'
	
	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	plane_title = StringField(ddl='varchar(20)')
	plane_content = StringField(ddl='varchar(100)')
	plane_state = StringField(ddl='varchar(10)')
	start_time = FloatField(default=time.time)
	end_time = FloatField(default=time.time)
	created_at = FloatField(default=time.time)

class Message(Model):
	__table__ = 'messages'
	
	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	recv_id = StringField(ddl='varchar(50)')
	title = StringField(ddl='varchar(20)')
	content = StringField(ddl='varchar(200)')
	created_at = FloatField(default=time.time)

class Advice(Model):
	__table__ = 'feedbacks_info'
	
	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	user_id = StringField(ddl='varchar(50)')
	title = StringField(ddl='varchar(20)')
	content = StringField(ddl='varchar(200)')
	created_at = FloatField(default=time.time)

class Sub_video(Model):
	__table__ = 'sub_video'
	
	id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
	parent_video_id = StringField(ddl='varchar(50)')
	title = StringField(ddl='varchar(50)')
	video_path = StringField(ddl='varchar(300)')
	num = StringField(ddl='int')
	created_at = FloatField(default=time.time)
