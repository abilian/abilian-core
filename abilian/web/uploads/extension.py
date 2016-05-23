# coding=utf-8
"""
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import json
import logging
import time
from datetime import timedelta
from uuid import UUID, uuid1

from celery import shared_task
from flask import current_app
from flask_login import AnonymousUserMixin

from abilian.core import signals
from abilian.web import url_for

from .views import bp as blueprint

logger = logging.getLogger(__name__)

CHUNK_SIZE = 64 * 1024

DEFAULT_CONFIG = {
    'USER_QUOTA': 100 * 1024**2,  # max 100 Mb for all current files
    'USER_MAX_FILES': 1000,  # max number of files per user
    'DELETE_STALLED_AFTER': 60 * 60 * 24  # delete files remaining after 1 day
}

CLEANUP_SCHEDULE_ID = __name__ + '.periodic_clean_upload_directory'
DEFAULT_CLEANUP_SCHEDULE = {
    'task': CLEANUP_SCHEDULE_ID,
    'schedule': timedelta(hours=1),
}


def is_valid_handle(handle):
    try:
        UUID(handle)
    except ValueError:
        return False

    return True


class FileUploadsExtension(object):
    """
    API for Out-Of-Band file uploads.

    Allow to manage files in forms: file is uploaded to an upload url, a handle is
    returned will be used in the form to refer to this uploaded filed.

    If the form fails to validate the uploaded file is not lost.

    A periodic task cleans the temporary repository.
    """

    def __init__(self, app):
        app.extensions['uploads'] = self
        app.add_template_global(self, 'uploads')
        app.register_blueprint(blueprint)
        signals.register_js_api.connect(self._do_register_js_api)

        self.config = {}
        self.config.update(DEFAULT_CONFIG)
        self.config.update(app.config.get('FILE_UPLOADS', {}))
        app.config['FILE_UPLOADS'] = self.config

        # celery schedule
        CELERYBEAT_SCHEDULE = app.config.setdefault('CELERYBEAT_SCHEDULE', {})
        if CLEANUP_SCHEDULE_ID not in CELERYBEAT_SCHEDULE:
            CELERYBEAT_SCHEDULE[CLEANUP_SCHEDULE_ID] = DEFAULT_CLEANUP_SCHEDULE

        path = self.UPLOAD_DIR = app.DATA_DIR / 'uploads'
        if not path.exists():
            path.mkdir(0o775)

        path.resolve()

    def _do_register_js_api(self, sender):
        app = sender
        js_api = app.js_api.setdefault('upload', {})
        js_api['newFileUrl'] = url_for('uploads.new_file')

    def user_dir(self, user):
        user_id = (str(user.id) if not isinstance(user, AnonymousUserMixin) else
                   'anonymous')
        return self.UPLOAD_DIR / user_id

    def add_file(self, user, file_obj, **metadata):
        """Add a new file.

        :returns: file handle
        """
        user_dir = self.user_dir(user)
        if not user_dir.exists():
            user_dir.mkdir(0o775)

        handle = str(uuid1())
        file_path = user_dir / handle

        with file_path.open('wb') as out:
            for chunk in iter(lambda: file_obj.read(CHUNK_SIZE), b''):
                out.write(chunk)

        if metadata:
            meta_file = user_dir / '{}.metadata'.format(handle)
            with meta_file.open('wb') as out:
                json.dump(metadata, out, skipkeys=True)

        return handle

    def get_file(self, user, handle):
        """Retrieve a file for a user.

        :returns: a :class:`pathlib.Path` instance to this file, or None if no file
        can be found for this handle.
        """
        user_dir = self.user_dir(user)
        if not user_dir.exists():
            return None

        if not is_valid_handle(handle):
            return None

        file_path = user_dir / handle

        if not file_path.exists() and not file_path.is_file():
            return None

        return file_path

    def get_metadata_file(self, user, handle):
        content = self.get_file(user, handle)
        if content is None:
            return None

        metafile = content.parent / '{}.metadata'.format(handle)
        if not metafile.exists():
            return None

        return metafile

    def get_metadata(self, user, handle):
        metafile = self.get_metadata_file(user, handle)
        if metafile is None:
            return {}

        try:
            with metafile.open('rb') as in_:
                meta = json.load(in_)
        except:
            meta = {}

        return meta

    def remove_file(self, user, handle):
        paths = (self.get_file(user, handle),
                 self.get_metadata_file(user, handle),)

        for file_path in paths:
            if file_path is not None:
                try:
                    file_path.unlink()
                except:
                    logger.exception('Error during remove file')

    def clear_stalled_files(self):
        """Scan upload directory and delete stalled files.

        Stalled files are files uploaded more than `DELETE_STALLED_AFTER` seconds
        ago.
        """
        # FIXME: put lock in directory?
        CLEAR_AFTER = self.config['DELETE_STALLED_AFTER']
        minimum_age = time.time() - CLEAR_AFTER

        for user_dir in self.UPLOAD_DIR.iterdir():
            if not user_dir.is_dir():
                logger.error('Found non-directory in upload dir: %r',
                             bytes(user_dir))
                continue

            for content in user_dir.iterdir():
                if not content.is_file():
                    logger.error('Found non-file in user upload dir: %r',
                                 bytes(content))
                    continue

                if content.stat().st_ctime < minimum_age:
                    content.unlink()


# Task scheduled to run every hour: make it expire after 50min.
@shared_task(expires=3000)
def periodic_clean_upload_directory():
    """This task should be run periodically.

    Default config sets up schedule using
    :data:`DEFAULT_CLEANUP_SCHEDULE`. `CELERYBEAT_SCHEDULE` key is
    :data:`CLEANUP_SCHEDULE_ID`.
    """
    uploads = current_app.extensions['uploads']
    uploads.clear_stalled_files()
