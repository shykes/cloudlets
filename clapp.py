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

    def get_metafile(self):
        return os.path.join(self.path, ".clapp", "meta")
    metafile = property(get_metafile)

    def get_meta(self):
        if os.path.exists(self.metafile):
            return simplejson.loads(file(self.metafile).read())
        return {}
    meta = property(get_meta)

    def get_config_schema(self):
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
            "items": dict([(key, {"type": "object", "items": section}) for (key, section) in schema_skeleton.items()])
        }
    config_schema = property(get_config_schema)

    def get_args_schema(self):
        return self.meta.get("args", {})
    args_schema = property(get_args_schema)

    def validate_config(self, config):
        jsonschema.validate(config, self.config_schema)

    def get_config_file(self):
        return os.path.join(self.path, ".clapp", "applied_config")
    config_file = property(get_config_file)

    def get_config(self):
        if not os.path.exists(self.config_file):
            return None
        return simplejson.loads(file(self.config_file).read())

    def set_config(self, config):
        if self.config:
            raise ValueError("Already configured: %s" % self.config)
        file(self.config_file, "w").write("")
        self.validate_config(config)
        for template in self.meta.get("templates", []):
            print "Applying template %s with %s" % (template, config)
            EJSTemplate(self.path + template).apply(self.path + template, config)
        file(self.config_file, "w").write(simplejson.dumps(config, indent=1))

    config = property(get_config, set_config)

def main(args):
    if len(args[1:]) < 2:
        print "Usage: %s image_path json_config" % args[0]
        return 1
    image_path = args[1]
    config = {
            "args"    : simplejson.loads(args[2]),
            "ip"      : {"interfaces": []},
            "dns"       : {"nameservers": []}
        }
    print "Configuring image %s with %s" % (image_path, config)
    Image(image_path).config = config

if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv))
