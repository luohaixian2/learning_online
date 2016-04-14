drop database if exists online_learning;

create database online_learning;

use online_learning;

grant select, insert, update, delete on online_learning.* to 'root'@'localhost' identified by 'LHX4878015';

/*用户表*/
create table users (
    `id` varchar(50) not null,
    `email` varchar(50) not null,
    `passwd` varchar(50) not null,
    `admin` bool not null,
    `name` varchar(50) not null,
    `image` varchar(500) not null,
    `created_at` real not null,
    unique key `idx_email` (`email`),
    key `idx_created_at` (`created_at`),
    primary key(`id`)
) engine=innodb default charset=utf8;

/*视频表*/
create table videos (
    `id` varchar(50) not null,
    `name` varchar(50) not null,
    `video_type` varchar(20) not null,
    `sub_video_type` varchar(20) not null,
    `pic_path` varchar(300) not null,
    `video_path` varchar(300) not null,
    `describe` varchar(200) not null,
    `user_id` varchar(50) not null,
    `price` double not null,
    `dir_num` int not null,
    `people_num` int not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;

/*视频评论表*/
create table video_comments (
    `id` varchar(50) not null,
    `video_id` varchar(50) not null,
    `content` varchar(100) not null,
    `path` varchar(500) not null,
    `user_id` varchar(50) not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;

/*用户学习计划表*/
create table study_planes (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `plane_content` varchar(100) not null,
    `start_time` real not null,
    `end_time` real not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;

/*用户教学视频收藏表*/
create table collection_videos (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `video_id` varchar(50) not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;

/*用户教学视频拥有表*/
create table having_videos (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `video_id` varchar(50) not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;

/*消息表*/
create table messages (
    `id` varchar(50) not null,
    `recv_id` varchar(50) not null,
    `content` varchar(200) not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;

/*反馈信息表*/
create table feedbacks_info (
    `id` varchar(50) not null,
    `user_id` varchar(50) not null,
    `content` varchar(500) not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;

/*日志记录表*/
create table logs_info (
    `id` varchar(50) not null,
    `reco_type` varchar(50) not null,
    `user_id` varchar(50) not null,
    `video_id` varchar(50) not null,
    `behavio` varchar(100) not null,
    `created_at` real not null,
    primary key (`id`)
) engine=innodb default charset=utf8;
