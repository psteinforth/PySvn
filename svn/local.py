import os
import collections

import xml.etree

import svn.constants
import svn.common

_STATUS_ENTRY = \
    collections.namedtuple(
        '_STATUS_ENTRY', [
            'name',
            'type_raw_name',
            'type',
            'revision',
        ])


class LocalClient(svn.common.CommonClient):
    def __init__(self, path_, *args, **kwargs):
        if os.path.exists(path_) is False:
            raise EnvironmentError("Path does not exist: %s" % path_)

        super(LocalClient, self).__init__(
            path_,
            svn.constants.LT_PATH,
            *args, **kwargs)

    def __repr__(self):
        return '<SVN(LOCAL) %s>' % self.path

    def add(self, rel_path, do_include_parents=False):
        args = [rel_path]

        if do_include_parents is True:
            args.append('--parents')

        self.run_command(
            'add',
            args,
            wd=self.path)

    def commit(self, message, rel_filepaths=[]):
        args = ['-m', message] + rel_filepaths

        output = self.run_command(
            'commit',
            args,
            wd=self.path)

    def update(self, rel_filepaths=[], revision=None):
        cmd = []
        if revision is not None:
            cmd += ['-r', str(revision)]
        cmd += rel_filepaths
        self.run_command(
            'update',
            cmd,
            wd=self.path)

    def cleanup(self, remove_unversioned=False, remove_ignored=False):
        if(remove_unversioned):
            for file in self.status():
                if(file.type == svn.constants.ST_UNVERSIONED):
                    # remove folders/files manually because parameter --remove-unversioned is not available in svn before version 1.9
                    self.__remove_recursively(os.path.abspath(file.name))

        if(remove_ignored):
            for file in self.status():
                if(file.type == svn.constants.ST_IGNORED):
                    # remove folders/files manually because parameter --remove-ignored is not available in svn before version 1.9
                    self.__remove_recursively(os.path.abspath(file.name)) 

        if((remove_unversioned and remove_ignored) == False):
            # remove write locks and so on only if remove_unversioned and remove_ignored are not set to achieve the same behaviour as the svn clients in version 1.9 and above
            self.run_command(
                'cleanup',
                [],
                wd=self.path)

    def __remove_recursively(self, path):
        # Remove files from directory
        if not os.path.isdir(path):
            os.remove(path)
            return # recursion anchor
        # Remove files and folders from subdirectory
        files=os.listdir(path)
        for x in files:
            fullpath=os.path.join(path, x)
            if os.path.isfile(fullpath):
                os.remove(fullpath) # remove files from subdirectory
            elif os.path.isdir(fullpath):
                self.__remove_recursively(fullpath) # remove folders from subdirectory recursively
        os.rmdir(path) # remove directory as soon as it is empty

    def status(self, rel_path=None):
        path = self.path
        if rel_path is not None:
            path += '/' + rel_path

        raw = self.run_command(
            'status',
            ['--no-ignore', '--xml', path],
            do_combine=True)

        root = xml.etree.ElementTree.fromstring(raw)

        list_ = root.findall('target/entry')
        for entry in list_:
            entry_attr = entry.attrib
            name = entry_attr['path']

            wcstatus = entry.find('wc-status')
            wcstatus_attr = wcstatus.attrib

            change_type_raw = wcstatus_attr['item']
            change_type = svn.constants.STATUS_TYPE_LOOKUP[change_type_raw]

            # This will be absent if the file is "unversioned". It'll be "-1"
            # if added but not committed.
            revision = wcstatus_attr.get('revision')
            if revision is not None:
                revision = int(revision)

            yield _STATUS_ENTRY(
                name=name,
                type_raw_name=change_type_raw,
                type=change_type,
                revision=revision
            )

    def remove(self, rel_path, do_keep_local=False, do_force=False):
        args = []

        if do_keep_local is True:
            args.append('--keep-local')

        if do_force is True:
            args.append('--force')

        args += [
            rel_path
        ]

        self.run_command(
            'rm',
            args)

    def revert(self, rel_filepaths=["."], depth="empty"):
        cmd = []
        if(depth in (
                    "empty", # only the target itself
                     "files", # the target and any immediate file children thereof
                     "immediates", # the target and any immediate children thereof
                     "infinity" # the target and all of its descendants — full recursion
                     )):
            cmd += ["--depth", depth]
            
        cmd += rel_filepaths
        self.run_command(
            'revert',
            cmd,
            wd=self.path
        )