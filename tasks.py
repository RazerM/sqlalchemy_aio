from invoke import Collection, task


@task
def build_docs(ctx, watch=False):
    if watch:
        ctx.run('sphinx-autobuild --open-browser --watch sqlalchemy_aio '
                '-b html docs docs/_build/html')
    else:
        ctx.run('sphinx-build -b html -W -E docs docs/_build/html')


@task
def release(ctx, version):
    ctx.run("git tag {0} -m '{0} release'".format(version))
    ctx.run('git push --tags')
    ctx.run('rm dist/*')
    ctx.run('python setup.py sdist bdist_wheel')
    ctx.run('twine upload dist/*')


docs = Collection('docs')
docs.add_task(build_docs, 'build')

namespace = Collection(release, docs)
