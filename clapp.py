#!/usr/bin/env python

from __future__ import with_statement

import os
import subprocess
import tempfile
import shutil
import simplejson as json

from system import System
from dotcloud.template import EJSTemplate
from dotcloud import js

class Image(dict):

    def __init__(self, path, system=None):
        self.path = os.path.abspath(path)
        self.system = system if system else System()
        self.js = js.Context()
        if os.path.exists(self.clappfile):
            js_code = file(self.clappfile).read()
        else:
            js_code = "layer = {'volumes': [], 'templates': []}"
        dict.__init__(self, self.js.eval(js_code))

    def get_rootfs(self):
        return self.path
    rootfs = property(get_rootfs)

    def get_clappfile(self):
        return os.path.join(self.path, ".clapp", "clapp.js")
    clappfile = property(get_clappfile)

    def _get_properties(self, this):
        print "Computing properties"
        self.js.bind("get_this", lambda: this)
        ret = self.js.eval("""
            {
                var props = {};
                for (var p in layer.properties) {
                    props[p] = layer.properties[p](get_this());
                }
                props
            }
        """)
        print "\t" + ", ".join(ret)
        return ret

    def _copy_rootfs(self, dest):
        print "Copying rootfs from %s" % self.rootfs
        self.system.sh(["rsync", "-aH", self.rootfs + "/", dest])

    def _copy_volumes(self, dest, **sources):
        for volume in self["volumes"]:
            name = volume["name"]
            if name not in sources:
                if volume.get("optional"):
                    print "Skipping volume %s" % name
                else:
                    raise Exception("Required volume '%s' has no source" % volume["name"])
            src = sources[name]
            print "Copying volume %s from %s" % (name, src)
            self.system.sh(["rsync", "-aH", src + "/", dest + volume["mountpoint"]])

    def _apply_templates(self, dest, this={}):
        for template in self["templates"]:
            print "Applying template %s (this=%s)" % (template, this)
            EJSTemplate(dest + template).apply(dest + template, {"layer": this})

    def compile(self, dest, volume_sources={}, **args):
        if not os.path.exists(dest):
            print "%s doesn't exist: creating" % dest
            os.makedirs(dest)
        print "Conflicts: %s" % self.conflicts(dest)
        this = {"args": args}
        this.update(self._get_properties(this))
        self._copy_rootfs(dest)
        self._copy_volumes(dest, **volume_sources)
        self._apply_templates(dest, this)

    def conflicts(self, dest):
        return []

def compile_layers(dest, layers, aufs_rw=None):
    if os.path.exists(dest):
        raise Exception("%s already exists" % dest)
    os.makedirs(dest)
    print "aufs_rw = %s" % aufs_rw
    if aufs_rw:
        cmd = ["mount", "-t", "aufs", "-o", "br:"+aufs_rw+"=rw:"+":".join(layer + "=ro" for layer in layers), "aufs", dest]
        print cmd
        subprocess.call(cmd)
    else:
        print "[0]\t\t%s" % dest
        for (i, layer) in enumerate(layers):
            print "[%s]\t\t%s" % (i + 1, layer)
            subprocess.call(["rsync", "-aH", layer+"/", dest])


class TempDir(object):

    def __init__(self):
        self.path = tempfile.mkdtemp()
        print "created: %s" % str(self)

    def __str__(self):
        return self.path

    def __enter__(self):
        pass

    def __exit__(self, *args, **kw):
        if str(self) in System().mounts:
            print "%s is mounted: unmounting" % self
            subprocess.call(["umount", str(self)])
        print "removing tempdir"
        shutil.rmtree(str(self))

class tmp_aufs_mount(TempDir):

    def __init__(self, src):
        self.src = src
        super(self.__class__, self).__init__()

    def __enter__(self):
        print "Mounting %s on %s" % (self.src, self.path)
        subprocess.call(["mount", "-t", "aufs", "-o", "br:"+self.src+"=ro", "aufs", self.path])

    def __exit__(self, *args, **kw):
        print "Unmounting %s" % self.path
        if self.path:
            subprocess.call(["umount", self.path])

def copy_changes(aufs_rw, dest):
    with tmp_aufs_mount(aufs_rw) as mnt:
        print dir(mnt)
        subprocess.call(["find", mnt.path])
