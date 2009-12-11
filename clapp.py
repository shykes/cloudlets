#!/usr/bin/env python

from __future__ import with_statement

import os
import subprocess
import tempfile
import shutil
import simplejson as simplejson

import js
import jsonschema
from ejs import EJSTemplate

class Image(object):

    def __init__(self, path):
        self.path = os.path.abspath(path)

    def get_clappfile(self):
        return os.path.join(self.path, ".clapp", "clapp.js")
    clappfile = property(get_clappfile)

    def get_meta(self):
        if os.path.exists(self.clappfile):
            return simplejson.loads(file(self.clappfile).read())
        return {}
    meta = property(get_meta)

    def get_config_schema(self):
        return self.meta.get("config", {})
    config_schema = property(get_config_schema)

    def validate_config(self, **config):
        jsonschema.validate(config, {"type": "object", "items": self.meta.get("config", {})})

    def configure(self, **config):
        self.validate_config(**config)
        template_args = {
            "config"    : config,
            "inet"      : [],
            "dns"       : {"nameservers": []}
        }
        for template in self.meta.get("templates", []):
            print "Applying template %s with %s" % (template, template_args)
            EJSTemplate(self.path + template).apply(self.path + template, template_args)

def main(args):
    if len(args[1:]) < 2:
        print "Usage: %s image_path json_config" % args[0]
        return 1
    print "Configuring image %s with %s" % (args[1], args[2])
    Image(args[1]).configure(**dict(simplejson.loads(args[2])))

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
