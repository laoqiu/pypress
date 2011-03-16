#! /usr/bin/env python
#coding=utf-8
"""
    views: link.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

from flask import Module, Response, request, flash, jsonify, g, current_app,\
    abort, redirect, url_for, session

from flaskext.babel import gettext as _

from pypress.helpers import render_template, cached
from pypress.permissions import auth, admin
from pypress.extensions import db

from pypress.models import Link
from pypress.forms import LinkForm

link = Module(__name__)

@link.route("/")
@link.route("/page/<int:page>/")
def index(page=1):
    
    links = Link.query

    if g.user is None:
        links = links.filter(Link.passed==True)

    page_obj = links.paginate(page=page, per_page=Link.PER_PAGE)

    page_url = lambda page: url_for("link.index",page=page)

    return render_template("blog/links.html", 
                            page_obj=page_obj,
                            page_url=page_url)


@link.route("/add/", methods=("GET","POST"))
def add():
    
    form = LinkForm()

    if form.validate_on_submit():
        
        link = Link()
        form.populate_obj(link)

        if g.user and g.user.is_moderator:
            link.passed = True

        db.session.add(link)
        db.session.commit()

        flash(_("Adding success"), "success")

        return redirect(url_for('link.index'))

    return render_template("blog/add_link.html", form=form)


@link.route("/<int:link_id>/pass/", methods=("POST",))
@auth.require(401)
def edit(link_id):

    link = Link.query.get_or_404(link_id)
    link.permissions.edit.test(403)

    link.passed = True
    db.session.commit()

    return jsonify(success=True,
                   link_id=link_id)


@link.route("/<int:link_id>/delete/", methods=("POST",))
@auth.require(401)
def delete(link_id):

    link = Link.query.get_or_404(link_id)
    link.permissions.delete.test(403)

    db.session.delete(link)
    db.session.commit()

    return jsonify(success=True,
                   link_id=link_id)

   
