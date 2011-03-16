#!/usr/bin/env python
#coding=utf-8

from flaskext.mail import Mail
from flaskext.sqlalchemy import SQLAlchemy
from flaskext.cache import Cache
from flaskext.uploads import UploadSet, IMAGES

__all__ = ['mail', 'db', 'cache', 'photos']

mail = Mail()
db = SQLAlchemy()
cache = Cache()
photos = UploadSet('photos', IMAGES)

