
from __future__ import with_statement

import os
import re
import sys
import tarfile
import subprocess
import tempfile
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
            "name"          : {"optional": False, "type": "string", "description": "Canonical name of the image. example: org.dotcloud.debian-lenny-i386"},
            "description"   : {"optional": True,  "type": "string", "description": "User-readable description of the image"},
            "arch"          : {"optional": True,  "type": "string", "description": "Hardware architecture. example: i386"},
            "args"          : {"optional": True,  "type": "object", "description": "List of accepted user-specified configuration arguments", "default": {}},
            "templates"     : {"optional": True,  "type": "array", "description": "List of files which are templates", "default": []},
            "persistent"    : {"optional": True,  "type": "array", "description": "List of files or directories holding persistent data", "default": []},
            "ignore"        : {"optional": True,  "type": "array", "description": "List of patterns for files whose changes should be ignored"}
        }
    }

    def validate(self):
        """Validate contents of the manifest against the cloudlets spec"""
        jsonschema.validate(dict(self), self.specs)

    def __init__(self, *args, **kw):
        dict.__init__(self, *args, **kw)
        self.validate()

class Image(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)

    def tar(self):
        """ Wrap the image in an uncompressed tar stream, ignoring volatile files, and write it to stdout """
        tar = tarfile.open("", mode="w|", fileobj=sys.stdout)
        for path in self.get_files(exclude=map(re.compile, self.manifest["ignore"])):
            tar.add(self.path + path, path, recursive=False)

    def get_files(self, include=[], exclude=[]):
        """ Iterate over all paths in the image. Paths are "chrooted", ie. relative to the image with a prefix of "/" """
        for (basepath, dpaths, fpaths) in os.walk(self.path, topdown=True):
            chrooted_basepath = "/" if basepath == self.path else basepath.replace(self.path, "")
            for subpath in dpaths + fpaths:
                path = os.path.join(chrooted_basepath, subpath)
                if filter_path(path, include, exclude):
                    yield path
    files = property(get_files)

    def chroot_path(self, path):
        if os.path.normpath(path) == self.path:
            return "/"
        return path.replace(self.path, "")

    def unchroot_path(self, path):
        return os.path.join(self.path, re.sub("^/+", "", path))

    def find(self, templates=False, ignore=False, persistent=False, other=False):
        include = []
        exclude = []
        if other:
            include = re.compile(".*")
            if not templates:
                exclude += self.manifest.get("templates", [])
            if not ignore:
                exclude += self.manifest.get("ignore", [])
            if not persistent:
                exclude += self.manifest.get("persistent", [])
        else:
            exclude = re.compile(".*")
            if templates:
                include += self.manifest.get("templates", [])
            if ignore:
                include += map(re.compile, self.manifest.get("ignore", []))
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
        return {}
    manifest = property(get_manifest)

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

    def get_args_schema(self):
        """ Return the json schema which will be used to validate the user-specified arguments as part of the image's overall configuration. """
        return self.manifest.get("args", {})
    args_schema = property(get_args_schema)

    def validate_config(self, config):
        """ Validate a configuration against the image's json schema. The configuration is not applied. """
        jsonschema.validate(config, self.config_schema)

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
        self.validate_config(config)
        for template in self.manifest.get("templates", []):
            print "Applying template %s with %s" % (template, config)
            EJSTemplate(self.path + template).apply(self.path + template, config)
        file(self.config_file, "w").write(simplejson.dumps(config, indent=1))

    config = property(get_config, set_config)
