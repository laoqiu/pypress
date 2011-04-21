#!/usr/bin/env python
#coding=utf-8
"""
    models: blog.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

import hashlib, re, random

from datetime import datetime

from werkzeug import cached_property

from flask import abort, current_app, url_for, Markup

from flaskext.babel import gettext as _
from flaskext.sqlalchemy import BaseQuery
from flaskext.principal import RoleNeed, UserNeed, Permission

from pypress import signals
from pypress.helpers import storage, slugify, markdown

from pypress.extensions import db
from pypress.permissions import moderator, admin

from pypress.models.users import User

class PostQuery(BaseQuery):

    def jsonify(self):
        for post in self.all():
            yield post.json

    def as_list(self):
        """
        Return restricted list of columns for list queries
        """

        deferred_cols = ("content", 
                         "tags",
                         "author.email",
                         "author.activation_key",
                         "author.date_joined",
                         "author.last_login",
                         "author.last_request")

        options = [db.defer(col) for col in deferred_cols]
        return self.options(*options)
    
    def get_by_slug(self, slug):
        post = self.filter(Post.slug==slug).first()
        if post is None:
            abort(404)
        return post
    
    def search(self, keywords):

        criteria = []

        for keyword in keywords.split():
            keyword = '%' + keyword + '%'
            criteria.append(db.or_(Post.title.ilike(keyword),
                                   Post.content.ilike(keyword),
                                   Post.tags.ilike(keyword)
                                   ))

        q = reduce(db.and_, criteria)
        return self.filter(q)

    def archive(self, year, month, day):
        if not year:
            return self
        
        criteria = []
        criteria.append(db.extract('year',Post.created_date)==year)
        if month: criteria.append(db.extract('month',Post.created_date)==month)
        if day: criteria.append(db.extract('day',Post.created_date)==day)
        
        q = reduce(db.and_, criteria)
        return self.filter(q)


class Post(db.Model):

    __tablename__ = 'posts'

    PER_PAGE = 40    
    
    query_class = PostQuery
    
    id = db.Column(db.Integer, primary_key=True)

    author_id = db.Column(db.Integer, 
                          db.ForeignKey(User.id, ondelete='CASCADE'), 
                          nullable=False)
    
    _title = db.Column("title", db.Unicode(100), index=True)
    _slug = db.Column("slug", db.Unicode(50), unique=True, index=True)
    content = db.Column(db.UnicodeText)
    num_comments = db.Column(db.Integer, default=0)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    _tags = db.Column("tags", db.Unicode(100), index=True)

    author = db.relation(User, innerjoin=True, lazy="joined")

    __mapper_args__ = {'order_by': id.desc()}
        
    class Permissions(object):
        
        def __init__(self, obj):
            self.obj = obj

        @cached_property
        def edit(self):
            return Permission(UserNeed(self.obj.author_id))
  
        @cached_property
        def delete(self):
            return Permission(UserNeed(self.obj.author_id)) & moderator
  
    def __init__(self, *args, **kwargs):
        super(Post, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.title
    
    def __repr__(self):
        return "<%s>" % self
    
    @cached_property
    def permissions(self):
        return self.Permissions(self)

    def _get_title(self):
        return self._title

    def _set_title(self, title):
        self._title = title.lower().strip()
        if self.slug is None:
            self.slug = slugify(title)[:50]

    title = db.synonym("_title", descriptor=property(_get_title, _set_title))
    
    def _get_slug(self):
        return self._slug

    def _set_slug(self, slug):
        if slug:
            self._slug = slugify(slug)

    slug = db.synonym("_slug", descriptor=property(_get_slug, _set_slug))
    
    def _get_tags(self):
        return self._tags 

    def _set_tags(self, tags):
        
        self._tags = tags

        if self.id:
            # ensure existing tag references are removed
            d = db.delete(post_tags, post_tags.c.post_id==self.id)
            db.engine.execute(d)

        for tag in set(self.taglist):

            slug = slugify(tag)

            tag_obj = Tag.query.filter(Tag.slug==slug).first()
            if tag_obj is None:
                tag_obj = Tag(name=tag, slug=slug)
                db.session.add(tag_obj)
            
            tag_obj.posts.append(self)

    tags = db.synonym("_tags", descriptor=property(_get_tags, _set_tags))
    
    @property
    def taglist(self):
        if self.tags is None:
            return []

        tags = [t.strip() for t in self.tags.split(",")]
        return [t for t in tags if t]

    @cached_property
    def linked_taglist(self):
        """
        Returns the tags in the original order and format, 
        with link to tag page
        """
        return [(tag, url_for('frontend.tag', 
                              slug=slugify(tag))) \
                for tag in self.taglist]
    
    @cached_property
    def summary(self):
        s = re.findall(r'(<p id="more\-(\d+)">)', self.content)
        if not s:
            return self.content
        p, more_id = s[0]
        addlink = '<p><a class="more-link" href="%s#more-%s">%s</a></p>' % (self.url, more_id, _("Read more..."))
        return self.content.split(p)[0] + addlink
    
    @cached_property
    def comments(self):
        """
        Returns comments in tree. Each parent comment has a "comments" 
        attribute appended and a "depth" attribute.
        """
        comments = Comment.query.filter(Comment.post_id==self.id).all()

        def _get_comments(parent, depth):
            
            parent.comments = []
            parent.depth = depth

            for comment in comments:
                if comment.parent_id == parent.id:
                    parent.comments.append(comment)
                    _get_comments(comment, depth + 1)

        parents = [c for c in comments if c.parent_id is None]

        for parent in parents:
            _get_comments(parent, 0)

        return parents

    @cached_property
    def json(self):
        """
        Returns dict of safe attributes for passing into 
        a JSON request.
        """
        
        return dict(id=self.id,
                    title=self.title,
                    content=self.content,
                    author=self.author.username)
    
    def _url(self, _external=False):
        return url_for('frontend.post', 
                       year=self.created_date.year,
                       month=self.created_date.month,
                       day=self.created_date.day,
                       slug=self.slug, 
                       _external=_external)

    @cached_property
    def url(self):
        return self._url()

    @cached_property
    def permalink(self):
        return self._url(True)
    

post_tags = db.Table("post_tags", db.Model.metadata,
    db.Column("post_id", db.Integer, 
              db.ForeignKey('posts.id', ondelete='CASCADE'), 
              primary_key=True),
    db.Column("tag_id", db.Integer, 
              db.ForeignKey('tags.id', ondelete='CASCADE'),
              primary_key=True))


class TagQuery(BaseQuery):

    def cloud(self):

        tags = self.filter(Tag.num_posts > 0).all()

        if not tags:
            return []

        max_posts = max(t.num_posts for t in tags)
        min_posts = min(t.num_posts for t in tags)

        diff = (max_posts - min_posts) / 10.0
        if diff < 0.1:
            diff = 0.1

        for tag in tags:
            tag.size = int(tag.num_posts / diff)
            if tag.size < 1: 
                tag.size = 1

        random.shuffle(tags)

        return tags
    

class Tag(db.Model):

    __tablename__ = "tags"
    
    query_class = TagQuery

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.Unicode(80), unique=True)
    posts = db.dynamic_loader(Post, secondary=post_tags, query_class=PostQuery)

    _name = db.Column("name", db.Unicode(80), unique=True)
    
    def __init__(self, *args, **kwargs):
        super(Tag, self).__init__(*args, **kwargs)
    
    def __str__(self):
        return self.name

    def _get_name(self):
        return self._name

    def _set_name(self, name):
        self._name = name.lower().strip()
        self.slug = slugify(name)

    name = db.synonym("_name", descriptor=property(_get_name, _set_name))

    @cached_property
    def url(self):
        return url_for("frontend.tag", slug=self.slug)

    num_posts = db.column_property(
        db.select([db.func.count(post_tags.c.post_id)]).\
            where(db.and_(post_tags.c.tag_id==id,
                          Post.id==post_tags.c.post_id)).as_scalar())


class Comment(db.Model):

    __tablename__ = "comments"

    PER_PAGE = 40    
    
    id = db.Column(db.Integer, primary_key=True)

    post_id = db.Column(db.Integer, 
                        db.ForeignKey(Post.id, ondelete='CASCADE'), 
                        nullable=False)

    author_id = db.Column(db.Integer, 
                          db.ForeignKey(User.id, ondelete='CASCADE')) 

    parent_id = db.Column(db.Integer, 
                          db.ForeignKey("comments.id", ondelete='CASCADE'))
    
    email = db.Column(db.String(50))
    nickname = db.Column(db.Unicode(50))
    website = db.Column(db.String(100))

    comment = db.Column(db.UnicodeText)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)

    ip = db.Column(db.Integer)

    _author = db.relation(User, backref="posts", lazy="joined")

    post = db.relation(Post, innerjoin=True, lazy="joined")

    parent = db.relation('Comment', remote_side=[id])

    __mapper_args__ = {'order_by' : id.asc()}
    
    class Permissions(object):
        
        def __init__(self, obj):
            self.obj = obj
        
        @cached_property
        def reply(self):
            return Permission(UserNeed(self.obj.post.author_id))

        @cached_property
        def delete(self):
            return Permission(UserNeed(self.obj.author_id),
                              UserNeed(self.obj.post.author_id)) & moderator

    def __init__(self, *args, **kwargs):
        super(Comment, self).__init__(*args, **kwargs)

    @cached_property
    def permissions(self):
        return self.Permissions(self)
    
    def _get_author(self):
        if self._author:
            return self._author
        return storage(email = self.email, 
                       nickname = self.nickname, 
                       website = self.website)

    def _set_author(self, author):
        self._author = author

    author = db.synonym("_author", descriptor=property(_get_author, _set_author))

    def _url(self, _external=False):
        return '%s#comment-%d' % (self.post._url(_external), self.id)

    @cached_property
    def url(self):
        return self._url()

    @cached_property
    def permalink(self):
        return self._url(True)

    @cached_property
    def markdown(self):
        return Markup(markdown(self.comment or ''))

   
class Link(db.Model):

    __tablename__ = "links"

    PER_PAGE = 80

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Unicode(50), nullable=False)
    link = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(100))
    description = db.Column(db.Unicode(100))
    email = db.Column(db.String(50))
    passed = db.Column(db.Boolean, default=False)
    created_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    class Permissions(object):
        
        def __init__(self, obj):
            self.obj = obj
        
        @cached_property
        def edit(self):
            return moderator

        @cached_property
        def delete(self):
            return moderator

    def __init__(self, *args, **kwargs):
        super(Link, self).__init__(*args, **kwargs)

    @cached_property
    def permissions(self):
        return self.Permissions(self)
    
    def __str__(self):
        return self.name

# ------------- SIGNALS ----------------#

def update_num_comments(sender):
    sender.num_comments = \
        Comment.query.filter(Comment.post_id==sender.id).count()
    db.session.commit()


signals.comment_added.connect(update_num_comments)
signals.comment_deleted.connect(update_num_comments)

