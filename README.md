A team blog based on [Flask](http://flask.pocoo.org/)
===

This project isn't supported at the moment, please see a newer [pypress-tornado](https://github.com/laoqiu/pypress-tornado)

Thanks for flask_website and newsmeme at [http://flask.pocoo.org/community/poweredby/]

##Install

###Prerequisite

	pip install -r requirements.txt

###Custom the Configuration
	
	pypress/config.cfg

###Sync database

	python manage.py createall

###Run

	python manage.py runserver

##Example
###Create Users

Admin:

	python manage.py createcode -r admin

Create three members in a batch:
	
	python manage.py createcode -r member -n 3

###Signup
	
	http://localhost:8080/account/signup/
