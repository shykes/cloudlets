
from __future__ import with_statement

import os
import re
import sys
import tarfile
import metashelf
import mercurial.hg, mercurial.ui, mercurial.error
import subprocess
from tempfile import mkdtemp, mktemp
import shutil
import simplejson as simplejson

import js
import jsonschema
from ejs import EJSTemplate

def filter_path(path, include, exclude):
    if not hasattr(include, "__iter__"):
        include = [include]
    if not hasattr(exclude, "__iter__"):
        exclude = [exclude]
    def match_filters(path, filters):
        return any([f.match(path) if hasattr(f, "match") else f == path for f in filters])
    return match_filters(path, include) or not match_filters(path, exclude)


class Manifest(dict):
    """A dictionary holding an image's metadata"""

    specs = {
        "type": "object",
        "properties": {
            "arch"          : {"optional": True,  "type": "string", "description": "Hardware architecture. example: i386"},
            "args"          : {"optional": True,  "type": "object", "description": "List of accepted user-specified configuration arguments", "default": {}},
            "templates"     : {"optional": True,  "type": "array", "description": "List of files which are templates", "default": []},
            "persistent"    : {"optional": True,  "type": "array", "description": "List of files or directories holding persistent data", "default": []},
            "volatile"      : {"optional": True,  "type": "array", "description": "List of patterns for files whose changes should be ignored"}
        }
    }

    def get_args_schema(self):
        """ Return the json schema which will be used to validate the user-specified arguments as part of the image's overall configuration. """
        return self.get("args", {})
    args_schema = property(get_args_schema)

    def get_config_schema(self):
        """ Return the json schema which will be used to validate this image's configuration. """
        schema_skeleton =  {
            "dns": {
                "nameservers": {"type": "array"}
            },
            "ip": {
                "interfaces": {"type": "array"}
            },
            "args": self.args_schema
        }
        return {
            "type": "object",
            "properties": dict([(key, {"type": "object", "properties": section}) for (key, section) in schema_skeleton.items()])
        }
    config_schema = property(get_config_schema)

    def validate_config(self, config):
        """ Validate a configuration against the image's json schema. The configuration is not applied. """
        jsonschema.validate(config, self.config_schema)

    def validate(self):
        """Validate contents of the manifest against the cloudlets spec"""
        jsonschema.validate(dict(self), self.specs)

    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self.validate()

class Image(object):

    def __init__(self, path):
        if not os.path.isdir(path):
            raise ValueError("%s doesn't exist or is not a directory" % path)
        self.path = os.path.abspath(path)

    def copy(self, dest=None, *args, **kw):
        """ Copy the image to a new directory at <dest>. If dest is None, a temporary directory is created. <dest> is returned. All options are passed to Image.tar() for lossless transfer. """
        if dest is None:
            dest = mkdtemp()
        tmptar = file(mktemp(), "wb")
        self.tar(out=tmptar, *args, **kw)
        tmptar.close()
        tarfile.open(tmptar.name, "r").extractall(dest)
        return dest

    def tar(self, out=sys.stdout, config=None, *args, **kw):
        """ Wrap the image in an uncompressed tar stream, ignoring volatile files, and write it to stdout """
        if config is not None:
            self.manifest.validate_config(config)
            templates_dir = self.copy(templates=True)
            for template in self.find(templates=True):
                EJSTemplate(templates_dir + template).apply(templates_dir + template, config)
        tar = tarfile.open("", mode="w|", fileobj=out)
        templates = self.manifest.get("templates")
        for path in self.find(*args, **kw):
            if config and path in templates:
                real_path = templates_dir + path
                EJSTemplate(real_path).apply(real_path, config)
            else:
                real_path = self.unchroot_path(path)
            tar.add(real_path, path, recursive=False)
        tar.close()

    def get_files(self, include=[], exclude=[]):
        """ Iterate over all paths in the image. Paths are "chrooted", ie. relative to the image with a prefix of "/" """
        for (basepath, dpaths, fpaths) in os.walk(self.path, topdown=True):
            for subpath in dpaths + fpaths:
                path = os.path.join(self.chroot_path(basepath), subpath)
                if filter_path(path, include, exclude):
                    yield path
    files = property(get_files)

    def chroot_path(self, path):
        if os.path.normpath(path) == self.path:
            return "/"
        return path.replace(self.path, "")

    def unchroot_path(self, path):
        return os.path.join(self.path, re.sub("^/+", "", path))

    def find(self, templates=False, volatile=False, persistent=False, other=False):
        include = []
        exclude = []
        if other:
            if not templates:
                exclude += self.manifest.get("templates", [])
            if not volatile:
                exclude += map(re.compile, self.manifest.get("volatile", []))
            if not persistent:
                exclude += self.manifest.get("persistent", [])
        else:
            exclude = re.compile(".*")
            if templates:
                include += self.manifest.get("templates", [])
            if volatile:
                include += map(re.compile, self.manifest.get("volatile", []))
            if persistent:
                include += self.manifest.get("persistent", [])
        return self.get_files(include=include, exclude=exclude)

    def get_cloudletdir(self):
        """ Return the path of the directory containing the image's metadata. """
        return os.path.join(self.path, ".cloudlet")
    cloudletdir = property(get_cloudletdir)

    def get_manifestfile(self):
        """ Return the manifest file containing the image's metadata. """
        return os.path.join(self.cloudletdir, "manifest")
    manifestfile = property(get_manifestfile)

    def get_manifest(self):
        """ Return a dictionary containing the image's metadata. """
        if os.path.exists(self.manifestfile):
            return Manifest(simplejson.loads(file(self.manifestfile).read()))
        return Manifest({})
    manifest = property(get_manifest)

    def get_config_file(self):
        """ Return the path to the file holding the currently applied configuration. If no configuration is applied, the file should not exist. """
        return os.path.join(self.cloudletdir, "applied_config")
    config_file = property(get_config_file)

    def get_config(self):
        """ Return a dictionary holding the configuration currently applied on the image. If no config is applied, return None."""
        if not os.path.exists(self.config_file):
            return None
        return simplejson.loads(file(self.config_file).read())

    def set_config(self, config):
        """ Apply a new configuration on the image. If a configuration is already in place, an exception will be raised. """
        if self.config:
            raise ValueError("Already configured: %s" % self.config)
        file(self.config_file, "w").write("")
        self.manifest.validate_config(config)
        for template in self.manifest.get("templates", []):
            print "Applying template %s with %s" % (template, config)
            EJSTemplate(self.unchroot_path(template)).apply(self.unchroot_path(template), config)
        file(self.config_file, "w").write(simplejson.dumps(config, indent=1))

    def hg(self, *cmd):
        """ Run a mercurial command, using the image as a repository """
        hgrc_path = os.path.join(self.path, ".hg", "hgrc")
        hgignore_path = os.path.join(self.path, ".hgignore")
        if os.path.exists(hgrc_path):
            os.unlink(hgrc_path)
        if os.path.exists(hgignore_path):
            os.unlink(hgignore_path)
        try:
            repo = mercurial.hg.repository(mercurial.ui.ui(), path=self.path, create=False)
        except mercurial.error.RepoError:
            repo = mercurial.hg.repository(mercurial.ui.ui(), path=self.path, create=True)
        ignore = ["^.hgignore$"] + [re.sub("^/", "^", p) for p in self.manifest.get("volatile", [])]
        file(hgignore_path, "w").write("\n".join(ignore))
        hgrc = """[hooks]
pre-commit.metashelf = python:metashelf.hg.hook_remember
pre-status.metashelf = python:metashelf.hg.hook_remember
pre-diff.metashelf = python:metashelf.hg.hook_remember
post-update.metashelf = python:metashelf.hg.hook_restore
        """
        file(hgrc_path, "w").write(hgrc)
        subprocess.call(("hg", "-R", self.path) + cmd)

    config = property(get_config, set_config)
