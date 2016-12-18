# coding: utf-8
from __future__ import absolute_import, division, print_function

from invoke import Collection, task


@task
def build_docs(ctx, watch=False):
    if watch:
        ctx.run('sphinx-autobuild --open-browser --watch sqlalchemy_aio '
                '-b html docs docs/_build/html')
    else:
        ctx.run('sphinx-build -b html -W -E docs docs/_build/html')

namespace = Collection()

docs = Collection('docs')
docs.add_task(build_docs, 'build')

namespace.add_collection(docs)
