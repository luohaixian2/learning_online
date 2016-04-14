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
