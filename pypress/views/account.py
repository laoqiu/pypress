#! /usr/bin/env python
#coding=utf-8
"""
    account.py
    ~~~~~~~~~~~~~
    :license: BSD, see LICENSE for more details.
"""

import datetime
import os, sys

# parse_qsl moved to urlparse module in v2.6
try:
  from urlparse import parse_qsl
except:
  from cgi import parse_qsl

import oauth2 as oauth

from flask import Module, Response, request, flash, jsonify, g, current_app,\
    abort, redirect, url_for, session

from flaskext.babel import gettext as _
from flaskext.principal import identity_changed, Identity, AnonymousIdentity

from pypress.helpers import render_template, cached
from pypress.permissions import auth, admin 
from pypress.extensions import db

from pypress.models import User, UserCode, Twitter
from pypress.forms import LoginForm, SignupForm

from pypress import twitter

account = Module(__name__)

REQUEST_TOKEN_URL = 'https://api.twitter.com/oauth/request_token'
ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'

@account.route("/login/", methods=("GET","POST"))
def login():
    
    form = LoginForm(login=request.args.get('login',None),
                     next=request.args.get('next',None))

    if form.validate_on_submit():

        user, authenticated = User.query.authenticate(form.login.data,
                                                      form.password.data)

        if user and authenticated:
            session.permanent = form.remember.data
            
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

            flash(_("Welcome back, %(name)s", name=user.username), "success")

            next_url = form.next.data

            if not next_url or next_url == request.path:
                next_url = url_for('frontend.people', username=user.username)

            return redirect(next_url)

        else:

            flash(_("Sorry, invalid login"), "error")

    return render_template("account/login.html", form=form)

    
@account.route("/signup/", methods=("GET","POST"))
def signup():
    
    form = SignupForm(next=request.args.get('next',None))

    if form.validate_on_submit():

        code = UserCode.query.filter_by(code=form.code.data).first()

        if code:
            user = User(role=code.role)
            form.populate_obj(user)

            db.session.add(user)
            db.session.delete(code)
            db.session.commit()

            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

            flash(_("Welcome, %(name)s", name=user.nickname), "success")

            next_url = form.next.data

            if not next_url or next_url == request.path:
                next_url = url_for('frontend.people', username=user.username)

            return redirect(next_url)
        else:
            form.code.errors.append(_("Code is not allowed"))

    return render_template("account/signup.html", form=form)

    
@account.route("/logout/")
def logout():

    flash(_("You are now logged out"), "success")
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())

    next_url = request.args.get('next','')

    if not next_url or next_url == request.path:
        next_url = url_for("frontend.index")

    return redirect(next_url)


@account.route("/twitter/")
@auth.require(401)
def twitter():

    if g.user.twitter:
        flash(_("You twitter's access token is already exists"), "error")
        return redirect(url_for('frontend.people', username=g.user.username))

    consumer_key = current_app.config['TWITTER_KEY']
    consumer_secret = current_app.config['TWITTER_SECRET']

    signature_method_hmac_sha1 = oauth.SignatureMethod_HMAC_SHA1()
    oauth_consumer             = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    oauth_client               = oauth.Client(oauth_consumer)
    
    try:
        resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')
    except AttributeError:
        flash(_("Can not connect twitter.com"))
        return redirect(url_for('frontend.people',username=g.user.username))

    if resp['status'] != '200':
        return 'Invalid respond from Twitter requesting temp token: %s' % resp['status']
    else:
        request_token = dict(parse_qsl(content))

        session['token'] = request_token

        return redirect('%s?oauth_token=%s' % (AUTHORIZATION_URL.replace("https:","http:"), 
                                               request_token['oauth_token']))


@account.route("/twitter/callback")
@auth.require(401)
def twitter_callback():
    token = oauth.Token(session['token']['oauth_token'], session['token']['oauth_token_secret'])
    verifier = request.args.get('oauth_verifier', '')
    token.set_verifier(verifier)

    consumer_key    = current_app.config['TWITTER_KEY']
    consumer_secret = current_app.config['TWITTER_SECRET']
    oauth_consumer  = oauth.Consumer(key=consumer_key, secret=consumer_secret)
    
    oauth_client  = oauth.Client(oauth_consumer, token)
    resp, content = oauth_client.request(ACCESS_TOKEN_URL, method='POST', body='oauth_verifier=%s' % verifier)
    access_token  = dict(parse_qsl(content))

    if resp['status'] != '200':
        return 'The request for a Token did not succeed: %s' % resp['status']
    else:
        if g.user.twitter is None:
            g.user.twitter = Twitter()
        
        g.user.twitter.token = access_token['oauth_token']
        g.user.twitter.token_secret = access_token['oauth_token_secret']

        db.session.commit()

        flash(_("Twitter request success"), "success")

        return redirect(url_for('frontend.people', username=g.user.username))


