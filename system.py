
import os
import re
import sys
from getopt import getopt
import subprocess

import simplejson

from dotcloud.utils import shellCommand, rsync

class dict_object(object):
    def __repr__(self):
        return repr(self.__dict__)

class Config(dict):

    def __init__(self, **override):
        super(self.__class__, self).__init__()
        config_search = os.environ.get("DOTCLOUD_CONFIG_PATH", "/etc/dotcloud").split(":")
        for (path, content) in self._load_files(*config_search):
            for (key, value) in content.items():
                self[key] = value
        for (key, value) in override.items():
            self[key] = value

    def _load_files(self, *search):

        def config_paths():
            for config_path in map(os.path.abspath, search):
                if os.path.isdir(config_path):
                    for (path, dirnames, filenames) in os.walk(config_path):
                        for filename in filenames:
                            yield os.path.normpath(os.path.join(path, filename))
                else:
                    yield os.path.normpath(config_path)
        
        for path in config_paths():
            try:
                yield (path, simplejson.loads(file(path).read()))
            except Exception, e:
                sys.stderr.write("Skipping %s: %s\n" % (path, e))
                continue

class Mount(dict_object):

    re_mount = re.compile("^(.*) on ([^ ]*) type (.*) \((.*)\)$")

    @classmethod
    def subclass(cls, mount_type):
        subcls = globals().get("%sMount" % mount_type.upper())
        if not subcls:
            return cls
        if not issubclass(subcls, cls):
            return cls
        return subcls

    @classmethod
    def _bindfs_sources(cls, system):
        return dict(
            [
                (mountpoint, source)
                for (mountpoint, source) in (
                    (
                        mountpoint if os.path.isabs(mountpoint) else os.path.join(basedir, mountpoint),
                        src if os.path.isabs(src) else os.path.join(basedir, src)
                    )
                    for (src, mountpoint), basedir in (
                        (
                            getopt(system.file("/proc/%s/cmdline" % pid).read().split("\x00")[1:], "vo:")[1][:2],
                            os.path.dirname(system.sh("cd /proc/%s/cwd; /bin/pwd" % pid))
                        )
                        for pid in system.sh("pidof bindfs").split()
                    )
                )
            ]
        )

    @classmethod
    def dict(cls, system):
        bindfs_sources = cls._bindfs_sources(system)
        return dict([
                    (mount.mountpoint, mount)
                    for mount in (
                            (cls.subclass(groups[0]))(
                                source      = groups[0] if groups[0] != "bindfs" else bindfs_sources.get(groups[1]),
                                mountpoint  = os.path.normpath(groups[1]),
                                type        = groups[2],
                                options     = groups[3].split(",")
                            )
                        for groups in (
                            line_match.groups()
                            for line_match in map(cls.re_mount.match, system.sh("mount").strip().split("\n"))
                            if line_match
                        )
                    )
                ])

    def __init__(self, source, mountpoint, type, options):
        self.source = source
        self.mountpoint = mountpoint
        self.type = type
        self.options = options

class AUFSMount(Mount):

    def get_layers(self):
        return [
            [
                dict(zip(("path", "access"), layer.split("=", 1)))
                for layer in option.split(":")[1:]
            ]
            for option in self.options
            if option.startswith("br:")
        ]
    layers = property(get_layers)

class Container(dict_object):

    @classmethod
    def dict(cls, system):
        return dict(
            [
                (container.name, container)
                for container in (
                    cls(
                        system  = system,
                        name    = words[0] if words[0] != "-" else words[1],
                        veid    = words[1],
                        ips=words[2:] if words[2:] != ["-"] else []
                    )
                    for words in [line.split() for line in  system.sh("vzlist -a -H -o name,veid,ip").split("\n") if line]
                )
            ]
        )

    def __init__(self, system, name, veid, ips):
        self.system = system
        self.name = name
        self.veid = veid
        self.ips = ips

    @classmethod
    def path_id(cls, path):
        try:
            return os.stat(path)[:2]
        except (OSError, IOError):
            return None

    @classmethod
    def create(cls, system, path, name):
        if name in system.containers:
            raise ValueError("Container %s already exists" % name)
        if callable(path):
            print "[...] Calling path hook..."
            path = path(system, name)
            print "[...] path hook returned '%s'" % path 
        conflicting_container = dict([(cls.path_id(container.root), container) for container in system.containers.values()]).get(cls.path_id(path))
        if conflicting_container:
            raise ValueError("'%s' is a hardlink to '%s', which is already used by container '%s' (%s)" % (path, conflicting_container.root, conflicting_container.name, conflicting_container.veid))
        if not os.path.exists('/etc/vz/dists/scripts/dotcloud.sh'):
            file('/etc/vz/dists/scripts/dotcloud.sh', 'w').write("#!/bin/bash\nexit 0")
        if not os.path.exists('/etc/vz/dists/dotcloud.conf'):
            file('/etc/vz/dists/dotcloud.conf', 'w').write("\n".join(
                "ADD_IP=dotcloud.sh",
                "DEL_IP=dotcloud.sh",
                "SET_HOSTNAME=dotcloud.sh",
                "SET_DNS=set_dns.sh",
                "SET_USERPASS=set_userpass.sh",
                "SET_UGID_QUOTA=set_ugid_quota.sh",
                "POST_CREATE=postcreate.sh"
            ))
        veids = [int(c.veid) for c in system.containers.values()]
        print "[...] Choosing a veid starting at 1000 which is not in %s" % list(veids)
        veid = (i for i in range(1000, max(veids) + 2) if i not in veids).next()
        print "[...] new veid: %s" % veid
        for (option, value) in (
                ('name',        name),
                ('applyconfig', 'vps.basic'),
                ('onboot',      'no'),
                ('ostemplate',  'dotcloud'),
                ('private',     path)
                ):
            system.sh("vzctl set %s --%s %s --save" % (veid, option, value))
        return system.containers.get(name)

    def as_dict(self):
        attributes = ("name", "veid", "ips", "root")
        return dict(zip(attributes, [getattr(self, attr) for attr in attributes]))
    def __repr__(self):
        return str(self.as_dict())

    def start(self):
        self.system.sh("vzctl start '%s'" % self.name)

    def get_ip(self):
        return sorted(self.ips)[0] if self.ips else None
    ip = property(get_ip)

    def get_root(self):
        return "/var/lib/vz/root/%s" % self.veid
    root = property(get_root)

    def get_mounts(self):
        return dict([
                (mountpoint.replace(self.root, ""), mount)
                for (mountpoint, mount) in self.system.mounts.items()
                if os.path.commonprefix((mountpoint, self.root)) == self.root
            ])
    mounts = property(get_mounts)


class System(object):

    def sh(self, cmd, **args):
        return subprocess.call(cmd, shell=True if type(cmd)==str else False, **args)

    def file(self, path, **args):
        return file(path, **args)

    def get_mtab(self):
        return self.file("/etc/mtab").read()
    mtab = property(get_mtab)

    def get_nameservers(self):
        return re.findall("^ *nameserver +([^ \n]+) *$", self.file("/etc/resolv.conf").read(), re.MULTILINE)
    nameservers = property(get_nameservers)

    def get_containers(self):
        return Container.dict(self)
    containers = property(get_containers)

    def create_container(self, path, name=None):
        return Container.create(self, path, name)

    def get_mounts(self):
        return Mount.dict(self)
    mounts = property(get_mounts)



class DotcloudSystem(System):

    def __init__(self, **config):
        self.config = config

    def get_root(self):
        return self.config["root"]
    root = property(get_root)

    def create_container(self, name, image_name):
        def mkpath(system, name):
            image_path = os.path.join(self.root, "images", image_name)
            if not os.path.exists(image_path):
                raise Exception("No such image: %s" % image_name)
            container_path = os.path.join(self.root, "containers", name)
            if os.path.exists(container_path):
                print "Warning: %s already exists. Overwriting." % container_path
            print "Copying %s to %s..." % (image_path, container_path)
            rsync(image_path, container_path)
            return container_path
        return super(self.__class__, self).create_container(mkpath, name)

