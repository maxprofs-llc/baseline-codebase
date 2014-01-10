#
# Copyright (c) 2014, Prometheus Research, LLC
#


"""
This package provides storage for uploaded files.
"""


from rex.core import (get_settings, Setting, Initialize, StrVal, MaybeVal,
        Error, cached)
from rex.web import HandleLocation, authorize
from webob import Response
from webob.dec import wsgify
from webob.static import FileIter, BLOCK_SIZE
from webob.exc import HTTPMethodNotAllowed, HTTPNotFound, HTTPUnauthorized
import re
import os
import datetime
import uuid
import mimetypes
import shutil
import cgi


def sanitize_filename(filename):
    """
    Sanitizes a string to make it safe for use as a filename.

    Any non-alphanumeric characters are removed; the length is restricted
    to 128 bytes.
    """
    assert isinstance(filename, (str, unicode))
    # Work in unicode so that `\w` matches non-Latin characters.
    if not isinstance(filename, unicode):
        filename = filename.decode('utf-8', 'replace')
    # Strip whitespaces and non-alphanumeric characters.
    filename = os.path.basename(filename)
    filename = filename.strip()
    filename = filename.replace(u' ', u'_')
    filename = re.sub(r'[^\w.-]', u'', filename, flags=re.U)
    # Deal with weird names.
    if not filename or filename.startswith(u'.'):
        filename = u'_'+filename
    if u'.' not in filename or filename.endswith(u'.'):
        filename = filename+u'.dat'
    # Limit the length.
    while len(filename.encode('utf-8')) > 128:
        l = len(filename)
        filename = filename[:l/3]+u'...'+filename[-l/3:]
    return filename.encode('utf-8')


class OpenFileApp(object):
    # Like `webob.static.FileApp`, but takes an open file object instead.

    def __init__(self, file):
        self.file = file

    @wsgify
    def __call__(self, req):
        # Adapted from `FileApp.__call__()`.
        if 'wsgi.file_wrapper' in req.environ:
            app_iter = req.environ['wsgi.file_wrapper'](self.file, BLOCK_SIZE)
        else:
            app_iter = FileIter(self.file)
        stat = os.fstat(self.file.fileno())
        last_modified = stat.st_mtime
        content_length = stat.st_size
        content_type, content_encoding = mimetypes.guess_type(self.file.name)
        content_disposition = "attachment; filename=%s" \
                % sanitize_filename(self.file.name)
        accept_ranges = 'bytes'
        return Response(
                app_iter=app_iter,
                last_modified=last_modified,
                content_length=content_length,
                content_type=content_type,
                content_encoding=content_encoding,
                content_disposition=content_disposition,
                accept_ranges=accept_ranges,
        ).conditional_response_app


class LocalStorage(object):
    """
    Stores attachments in the local file system.

    `attach_dir`
        Directory where attachments are stored.  Must exist and be writable.
    """

    # Attachment handles must match the pattern:
    #   /YYYY/MM/DD/{uuid}/{filename}
    handle_re = re.compile(r'''
        \A
        / [0-9]{4}
        / [0-9]{2}
        / [0-9]{2}
        / [0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}
        / [\w-][\w.-]*
        \Z''', re.X|re.U)

    def __init__(self, attach_dir):
        self.attach_dir = attach_dir

    def add(self, name, content=None):
        """
        Adds an attachment to the storage.

        `name`
            The name of the attachment (the filename).

        `content`
            The attachment content; either a string or an open file object.

        If ``content`` is ``None``, the ``name`` must be either a
        ``cgi.FieldStorage`` instance that wraps an uploaded file or a tuple
        with two elements: ``name`` and ``content``.

        Returns an opaque attachment handle.
        """
        if content is None:
            # Extract the attachment content from a `cgi.FieldStorage` object
            # or a tuple.
            if isinstance(name, cgi.FieldStorage):
                name, content = name.filename, name.file
            else:
                name, content = name
        # Sanitize the file name.
        name = sanitize_filename(name)
        # The directory where we save the file:
        #   `{attach_dir}/YYYY/MM/DD/{uuid}/`.
        target_dir = self.attach_dir
        # Create `/YYYY/MM/DD` directories.
        today = datetime.date.today()
        for fmt in ('%Y', '%m', '%d'):
            target_dir = os.path.join(target_dir, today.strftime(fmt))
            try:
                os.mkdir(target_dir)
            except OSError:
                if not os.path.isdir(target_dir):
                    raise
        # Create a temporary directory: `/YYYY/MM/DD/{uuid}.adding/`.
        random_uuid = str(uuid.uuid4())
        target_dir = os.path.join(target_dir, random_uuid)
        tmp_dir = target_dir+'.adding'
        os.mkdir(tmp_dir)
        # Save the attachment to the temporary directory.
        path = os.path.join(tmp_dir, name)
        with open(path, 'wb') as stream:
            if hasattr(content, 'read'):
                shutil.copyfileobj(content, stream)
            else:
                stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # Rename `/YYYY/MM/DD/{uuid}.adding/` to `/YYYY/MM/DD/{uuid}/`.
        os.rename(tmp_dir, target_dir)
        # Generate and return the attachment handle (which coincides with
        # the path to the attachment relative to `attach_dir`).
        handle = '/'+today.strftime('%Y/%m/%d')+'/'+random_uuid+'/'+name
        return handle

    def abspath(self, handle):
        # Converts an attachment handle to a path.  Verifies that the handle
        # is well-formed, but does not check if the file exists.
        if isinstance(handle, str):
            handle = handle.decode('utf-8', 'replace')
        if not self.handle_re.match(handle):
            raise Error("Ill-formed attachment handle:", handle.encode('utf-8'))
        return os.path.join(self.attach_dir, handle.encode('utf-8')[1:])

    def open(self, handle):
        """
        Gets an attachment by attachment handle.

        Returns an open file object.
        """
        path = self.abspath(handle)
        try:
            return open(path, 'rb')
        except IOError:
            if not os.path.exists(path):
                raise Error("Attachment does not exist:", handle)
            raise

    def remove(self, handle):
        """
        Deletes an attachment.
        """
        # Protect against ill-formed and unknown handles.
        path = self.abspath(handle)
        if not os.path.exists(path):
            raise Error("Attachment does not exist:", handle)
        # Start with renaming the attachment directory.
        target_dir = os.path.dirname(path)
        name = os.path.basename(path)
        tmp_dir = target_dir+'.removing'
        tmp_path = os.path.join(tmp_dir, name)
        try:
            os.rename(target_dir, tmp_dir)
        except OSError:
            # Race condition?
            if not os.path.exists(path):
                raise Error("Attachment does not exist:", handle)
            raise
        # Remove the attachment and the temporary directory.
        os.unlink(tmp_path)
        os.rmdir(tmp_dir)

    def stat(self, handle):
        """
        Gets information about the attachment.

        Returns a named tuple in format produced by ``os.stat()``.
        """
        path = self.abspath(handle)
        try:
            return os.stat(path)
        except OSError:
            if not os.path.exists(path):
                raise Error("Attachment does not exist:", handle)
            raise

    def __iter__(self):
        """
        Generates handles for all attachments in the storage.
        """
        # Emit all files that have a well-formed handle for a path.
        for handle in self._listdir(self.attach_dir):
            if self.handle_re.match(handle.decode('utf-8', 'replace')):
                yield handle

    def _listdir(self, base_dir):
        # Emits handles for all files in the given directory.
        for path in sorted(os.listdir(base_dir)):
            handle = '/'+path
            path = os.path.join(base_dir, path)
            if os.path.isfile(path):
                yield handle
            elif os.path.isdir(path):
                prefix = handle
                for handle in self._listdir(path):
                    yield prefix+handle

    def route(self, handle):
        """
        Returns a WSGI application that serves the given attachment.
        """
        file = self.open(handle)
        return OpenFileApp(file)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.attach_dir)


class AttachDirSetting(Setting):
    """
    Directory where to save uploaded files and other attachments.

    Example::

        attach_dir: /srv/rexdb/attachments
    """

    name = 'attach_dir'
    validate = StrVal()


class AttachAccessSetting(Setting):
    """
    Permission required for unrestricted access to the attachment storage.

    The default value is ``None``, which disables access to the storage.

    Example::

        attach_access: architect
    """

    name = 'attach_access'
    validate = MaybeVal(StrVal)
    default = None


class InitializeAttach(Initialize):
    # Verifies that `attach_dir` is a valid directory and writable.

    def __call__(self):
        settings = get_settings()
        attach_dir = settings.attach_dir
        if not os.path.isdir(attach_dir):
            raise Error("Attachment storage does not exist:", attach_dir)
        if not os.access(attach_dir, os.R_OK|os.W_OK|os.X_OK):
            raise Error("Attachment storage is not accessible:", attach_dir)


class HandleAttachLocation(HandleLocation):
    # Serves all attachments by handle.

    path = '*'

    def __call__(self, req):
        settings = get_settings()
        # Check if the service is enabled.
        if settings.attach_access is None:
            raise HTTPNotFound()
        # Check if the request has access to the service.
        if not authorize(req, settings.attach_access):
            raise HTTPUnauthorized()
        # Allow only GET and HEAD requests.
        if req.method not in ('GET', 'HEAD'):
            raise HTTPMethodNotAllowed()
        # Forward the request to the gateway object.
        storage = get_storage()
        try:
            handler = storage.route(req.path_info)
        except Error:
            raise HTTPNotFound()
        return handler(req)


@cached
def get_storage():
    """
    Returns an attachment storage object for the current Rex application.
    """
    settings = get_settings()
    return LocalStorage(settings.attach_dir)


