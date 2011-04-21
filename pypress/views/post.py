#! /usr/bin/env python
#coding=utf-8
"""
    views: post.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

import datetime
import os
import json

from flask import Module, Response, request, flash, jsonify, g, current_app, \
    abort, redirect, url_for, session

from flaskext.mail import Message
from flaskext.babel import gettext as _

from pypress import signals
from pypress.helpers import render_template, cached, ip2long
from pypress.permissions import auth 
from pypress.extensions import db

from pypress.models import User, Post, Comment
from pypress.forms import PostForm, CommentForm

post = Module(__name__)


@post.route("/", methods=("GET","POST"))
@auth.require(401)
def submit():
    
    form = PostForm()

    if form.validate_on_submit():

        post = Post(author=g.user)
        form.populate_obj(post)
        
        db.session.add(post)
        db.session.commit()

        flash(_("Posting success"), "success")

        return redirect(post.url)

    return render_template("blog/submit.html", form=form)


@post.route("/<int:post_id>/", methods=("GET","POST"))
def view(post_id):

    post = Post.query.get_or_404(post_id)

    return redirect(post.url)


@post.route("/<int:post_id>/edit/", methods=("GET","POST"))
@auth.require(401)
def edit(post_id):

    post = Post.query.get_or_404(post_id)

    form = PostForm(title = post.title, 
                    slug = post.slug,
                    content = post.content, 
                    tags = post.tags,
                    obj = post)

    if form.validate_on_submit():
        
        form.populate_obj(post)

        db.session.commit()
        
        flash(_("Post has been changed"), "success")
        
        return redirect(post.url)

    return render_template("blog/submit.html", form=form)


@post.route("/<int:post_id>/delete/", methods=("GET","POST"))
@auth.require(401)
def delete(post_id):

    post = Post.query.get_or_404(post_id)
    post.permissions.delete.test(403)

    Comment.query.filter_by(post=post).delete()
    
    db.session.delete(post)
    db.session.commit()
    
    if g.user.id != post.author_id:
        body = render_template("emails/post_deleted.html",
                               post=post)

        message = Message(subject="Your post has been deleted",
                          body=body,
                          recipients=[post.author.email])

        mail.send(message)

    flash(_("The post has been deleted"), "success")

    return jsonify(success=True,
                   redirect_url=url_for('frontend.index'))


@post.route("/<int:post_id>/addcomment/", methods=("GET", "POST"))
@post.route("/<int:post_id>/<int:parent_id>/reply/", methods=("GET", "POST"))
def add_comment(post_id, parent_id=None):

    post = Post.query.get_or_404(post_id)

    parent = Comment.query.get_or_404(parent_id) if parent_id else None
    
    form = CommentForm()

    if form.validate_on_submit():

        comment = Comment(post=post,
                          parent=parent,
                          ip=ip2long(request.environ['REMOTE_ADDR']))
        form.populate_obj(comment)

        if g.user:
            comment.author = g.user

        db.session.add(comment)
        db.session.commit()
        
        signals.comment_added.send(post)

        flash(_("Thanks for your comment"), "success")

        return redirect(comment.url)
    
    return render_template("blog/add_comment.html",
                           parent=parent,
                           post=post,
                           form=form)


