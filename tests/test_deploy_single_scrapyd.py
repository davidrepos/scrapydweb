# coding: utf8
import os
import io
import re
from functools import partial

from flask import url_for

from scrapydweb.vars import DEMO_PROJECTS_PATH
from tests.utils import CWD, PROJECT, VERSION, WINDOWS_NOT_CP936, SCRAPY_CFG_DICT
from tests.utils import req_single_scrapyd, set_single_scrapyd, upload_file_deploy


def test_auto_eggifying_select_option(app, client):
    ins = [
        '(14 projects)',
        u"var folders = ['ScrapydWeb-demo', 'demo - 副本', 'demo',",
        "var projects = ['ScrapydWeb-demo', 'demo-copy', 'demo',",
        '<div>%s<' % PROJECT,
        u'<div>demo - 副本<',
        '<div>demo<',
        '<div>demo_only_scrapy_cfg<'
    ]
    nos = ['<div>demo_without_scrapy_cfg<', '<h3>NO projects found']
    req_single_scrapyd(app, client, view='deploy.deploy', kws=dict(node=1), ins=ins, nos=nos)

    for project in [PROJECT, 'demo']:
        with io.open(os.path.join(CWD, 'data/%s/test' % project), 'w', encoding='utf8') as f:
            f.write(u'')
        ins = ['id="folder_selected" value="%s"' % project, 'id="folder_selected_statement">%s<' % project]
        req_single_scrapyd(app, client, view='deploy.deploy', kws=dict(node=1), ins=ins)

    with io.open(os.path.join(CWD, 'data/demo/test'), 'w', encoding='utf8') as f:
        f.write(u'')

    # SCRAPY_PROJECTS_DIR=os.path.join(CWD, 'data'),
    app.config['SCRAPY_PROJECTS_DIR'] = os.path.join(CWD, 'not-exist')
    req_single_scrapyd(app, client, view='deploy.deploy', kws=dict(node=1),
                       ins=['(0 projects)', '<h3>NO projects found'])

    app.config['SCRAPY_PROJECTS_DIR'] = os.path.join(CWD, 'data', 'one_project_inside')
    req_single_scrapyd(app, client, view='deploy.deploy', kws=dict(node=1),
                       ins='(1 project)', nos='<h3>NO projects found')

    app.config['SCRAPY_PROJECTS_DIR'] = ''
    req_single_scrapyd(app, client, view='deploy.deploy', kws=dict(node=1),
                       ins=DEMO_PROJECTS_PATH, nos='<h3>NO projects found')


# {'status': 'error', 'message': 'Traceback
# ...TypeError:...activate_egg(eggpath)...\'tuple\' object is not an iterator\r\n'}
def test_addversion(app, client):
    data = {
        'project': 'fakeproject',
        'version': 'fakeversion',
        'file': (io.BytesIO(b'my file contents'), "fake.egg")
    }
    req_single_scrapyd(app, client, view='deploy.upload', kws=dict(node=1), data=data, ins='activate_egg')


# <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
# <title>Redirecting...</title>
# <h1>Redirecting...</h1>
# <p>You should be redirected automatically to target URL:
# <a href="/1/schedule/demo/2018-01-01T01_01_01/">/1/schedule/demo/2018-01-01T01_01_01/</a>.  If not click the link.
def test_auto_eggifying(app, client):
    data = {
        'folder': PROJECT,
        'project': PROJECT,
        'version': VERSION,
    }
    with app.test_request_context():
        # http://localhost/1/schedule/ScrapydWeb-demo/2018-01-01T01_01_01/
        req_single_scrapyd(app, client, view='deploy.upload', kws=dict(node=1), data=data,
                           location=url_for('schedule.schedule', node=1, project=PROJECT, version=VERSION))


def test_auto_eggifying_unicode(app, client):
    if WINDOWS_NOT_CP936:
        return
    data = {
        'folder': u'demo - 副本',
        'project': u'demo - 副本',
        'version': VERSION,
    }
    with app.test_request_context():
        req_single_scrapyd(app, client, view='deploy.upload', kws=dict(node=1), data=data,
                           location=url_for('schedule.schedule', node=1, project='demo-', version=VERSION))


def test_scrapy_cfg(app, client):
    with app.test_request_context():
        for folder, result in SCRAPY_CFG_DICT.items():
            data = {
                'folder': folder,
                'project': PROJECT,
                'version': VERSION,
            }
            if result:
                req_single_scrapyd(app, client, view='deploy.upload', kws=dict(node=1), data=data, ins=result)
            else:
                req_single_scrapyd(app, client, view='deploy.upload', kws=dict(node=1), data=data,
                                   location=url_for('schedule.schedule', node=1, project=PROJECT, version=VERSION))


def test_scrapy_cfg_node_not_exist(app, client):
    with app.test_request_context():
        for folder, result in SCRAPY_CFG_DICT.items():
            data = {
                'folder': folder,
                'project': PROJECT,
                'version': VERSION,
            }
            nos = []
            if folder == 'demo_only_scrapy_cfg' or not result:
                ins = 'Fail to deploy project, got status'
            else:
                ins = ['Fail to deploy', result]
                nos = 'got status'
            req_single_scrapyd(app, client, view='deploy.upload', kws=dict(node=1), data=data,
                               ins=ins, nos=nos, set_to_second=True)


def test_upload_file_deploy(app, client):
    set_single_scrapyd(app)

    upload_file_deploy_singlenode = partial(upload_file_deploy, app=app, client=client, multinode=False)

    filenames = ['demo.egg', 'demo_inner.zip', 'demo_outer.zip',
                 'demo - Win7CNsendzipped.zip', 'demo - Win10cp1252.zip']
    if WINDOWS_NOT_CP936:
        filenames.extend(['demo - Ubuntu.zip', 'demo - Ubuntu.tar.gz', 'demo - macOS.zip', 'demo - macOS.tar.gz'])
    else:
        filenames.extend([u'副本.zip', u'副本.tar.gz', u'副本.egg', u'demo - 副本 - Win7CN.zip',
                          u'demo - 副本 - Win7CNsendzipped.zip', u'demo - 副本 - Win10cp936.zip',
                          u'demo - 副本 - Ubuntu.zip', u'demo - 副本 - Ubuntu.tar.gz',
                          u'demo - 副本 - macOS.zip', u'demo - 副本 - macOS.tar.gz'])

    for filename in filenames:
        if filename == 'demo.egg':
            project = PROJECT
            redirect_project = PROJECT
        else:
            project = re.sub(r'\.egg|\.zip|\.tar\.gz', '', filename)
            project = 'demo_unicode' if project == u'副本' else project
            redirect_project = re.sub(r'[^0-9A-Za-z_-]', '', project)
        upload_file_deploy_singlenode(filename=filename, project=project, redirect_project=redirect_project)

    for filename, alert in SCRAPY_CFG_DICT.items():
        if alert:
            upload_file_deploy_singlenode(filename='%s.zip' % filename, project=filename, alert=alert, fail=True)
        else:
            upload_file_deploy_singlenode(filename='%s.zip' % filename, project=filename, redirect_project=filename)

    app.config['SCRAPYD_SERVERS'] = ['not-exist:6801']

    for filename, alert in SCRAPY_CFG_DICT.items():
        if filename == 'demo_only_scrapy_cfg' or not alert:
            alert = 'Fail to deploy project, got status'
        upload_file_deploy_singlenode(filename='%s.zip' % filename, project=filename, alert=alert, fail=True)