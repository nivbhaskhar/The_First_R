#!/bin/bash

. venv/bin/activate

export DATABASE_URL=

export FLASK_APP=application.py

export GOODREADS_KEY=

#export TEMPLATES_AUTO_RELOAD=True

flask run
