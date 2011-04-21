#! /usr/bin/env python
#coding=utf-8
"""
    frontend.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

import datetime
import os

from flask import Module, Response, request, flash, jsonify, g, current_app,\
    abort, redirect, url_for, session, send_file, send_from_directory

from flaskext.babel import gettext as _

from pypress.helpers import render_template, cached
from pypress.permissions import auth, admin 
from pypress.extensions import db, photos

from pypress.models import User, Post, Comment, Tag
from pypress.forms import CommentForm, TemplateForm, TwitterForm

frontend = Module(__name__)

@frontend.route("/")
@frontend.route("/page/<int:page>/")
@frontend.route("/<int:year>/")
@frontend.route("/<int:year>/page/<int:page>/")
@frontend.route("/<int:year>/<int:month>/")
@frontend.route("/<int:year>/<int:month>/page/<int:page>/")
@frontend.route("/<int:year>/<int:month>/<int:day>/")
@frontend.route("/<int:year>/<int:month>/<int:day>/page/<int:page>/")
def index(year=None, month=None, day=None, page=1):

    if page<1:page=1

    page_obj = Post.query.archive(year,month,day).as_list() \
                         .paginate(page, per_page=Post.PER_PAGE)

    page_url = lambda page: url_for("post.index",
                                    year=year,
                                    month=month,
                                    day=day,
                                    page=page)

    return render_template("blog/list.html",
                            page_obj=page_obj,
                            page_url=page_url)


@frontend.route("/search/")
@frontend.route("/search/page/<int:page>/")
def search(page=1):
    
    keywords = request.args.get('q','').strip()

    if not keywords:
        return redirect(url_for("frontend.index"))

    page_obj = Post.query.search(keywords).as_list() \
                         .paginate(page, per_page=Post.PER_PAGE)

    if page_obj.total == 1:

        post = page_obj.items[0]
        return redirect(post.url)
    
    page_url = lambda page: url_for('frontend.search', 
                                    page=page,
                                    keywords=keywords)

    return render_template("blog/search_result.html",
                           page_obj=page_obj,
                           page_url=page_url,
                           keywords=keywords)


@frontend.route("/archive/")
def archive():
    
        
    return render_template("blog/archive.html")


@frontend.route("/tags/")
def tags():

    return render_template("blog/tags.html")


@frontend.route("/tags/<slug>/")
@frontend.route("/tags/<slug>/page/<int:page>/")
def tag(slug, page=1):

    tag = Tag.query.filter_by(slug=slug).first_or_404()

    page_obj = tag.posts.as_list() \
                        .paginate(page, per_page=Post.PER_PAGE)

    page_url = lambda page: url_for("post.tag",
                                    slug=slug,
                                    page=page)

    return render_template("blog/list.html",
                            page_obj=page_obj,
                            page_url=page_url)


@frontend.route("/people/<username>/", methods=("GET","POST"))
@frontend.route("/people/<username>/page/<int:page>/", methods=("GET","POST"))
def people(username, page=1):

    people = User.query.get_by_username(username)
    
    form = TwitterForm()

    if form.validate_on_submit():
        
        api = people.twitter_api

        if api is None:
            return redirect(url_for('account.twitter'))

        content = form.content.data.encode("utf8")
        
        status = people.post_twitter(content)
        
        if status:
            flash(_("Twitter posting is success"), "success")

            return redirect(url_for('frontend.people', 
                                    username=username,
                                    page=page))
        else:
            flash(_("Twitter posting is failed"), "error")

    page_obj = Post.query.filter(Post.author_id==people.id).as_list() \
                         .paginate(page, per_page=Post.PER_PAGE)
    
    page_url = lambda page: url_for("post.people",
                                    username=username,
                                    page=page)

    return render_template("blog/people.html",
                            form=form,
                            page_obj=page_obj,
                            page_url=page_url,
                            people=people)


@frontend.route("/upload/", methods=("POST",))
@auth.require(401)
def upload():

    if 'Filedata' in request.files:
        filename = photos.save(request.files['Filedata'])
        return json.dumps({'imgUrl':photos.url(filename)})

    return json.dumps({'error':_("Please select a picture")})


@frontend.route("/about/")
def about():
    return render_template("blog/about.html")


@frontend.route("/<int:year>/<int:month>/<int:day>/<slug>/")
def post(year, month, day, slug):
    
    post = Post.query.get_by_slug(slug)
    
    date = (post.created_date.year,
            post.created_date.month,
            post.created_date.day)
    
    if date != (year, month, day):
        return redirect(post.url)

    prev_post = Post.query.filter(Post.created_date<post.created_date) \
                          .first()
    next_post = Post.query.filter(Post.created_date>post.created_date) \
                          .order_by('created_date asc').first()
    
    return render_template("blog/view.html", 
                            post=post,
                            prev_post=prev_post,
                            next_post=next_post,
                            comment_form=CommentForm())


@frontend.route("/<slug>/")
@frontend.route("/<path:date>/<slug>/")
def _post(slug, date=None):

    post = Post.query.get_by_slug(slug)

    return redirect(post.url)


@frontend.route("/template/<path:path>/", methods=("GET","POST"))
@admin.require(401)
def template_edit(path):

    path = os.path.join(current_app.root_path, 'templates', "%s.html" % path)
    html = ""

    try:
        f = open(path)
        html = f.read()
        f.close()
    except:
        flash(_("Template file does not exists"), "error")

    form = TemplateForm(html=html.decode('utf8'))

    if form.validate_on_submit():

        f = open(path, 'w')
        f.write(form.html.data.encode('utf8'))
        f.close()

        flash(_("Saving success"), "success")

        return redirect(url_for("frontend.index"))

    return render_template("blog/template_edit.html",
                            form=form,
                            path=path)


@frontend.route("/favicon.ico")
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


