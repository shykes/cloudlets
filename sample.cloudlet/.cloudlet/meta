{
    "author":       "Solomon Hykes <solomon.hykes@dotcloud.com>",
    "description":  "Debian (Lenny/5.0) base system for i386",
    "arch":         "i386",
    "name":         "debian-5.0",

    "args": {
        "hostname"  : {"type": "string", "default": "debian-host"}
    },

    "templates": [
        "/etc/hostname"
    ],

    "persistent": [
        "/var/log"
    ],

    "ignore": [
        "/etc/rc6.d/S00vzreboot$",
        "/var/log/(?!apt).+",
        "/var/log/apt/.+",
        "/var/run/.+",
        "/sys/.+",
        "/proc/.+",
        "/var/tmp/.+",
        "/tmp/.+",
        "/var/cache/apt/archives/lock$",
        "/etc/mtab$",
        "/etc/nologin$",
        "/dev/log$",
        "/var/lib/urandom/random-seed$",
        "/usr/lib/python2.6/.+\\.pyc",
        "/var/lib/apt/lists/(?!partial).+",
        "/var/lib/apt/lists/partial/.+",
        "/var/cache/apt/pkgcache.bin$",
        "/var/cache/apt/srcpkgcache.bin$",
        "/var/cache/apt/archives/.+\\.deb",
        "/var/cache/apt/archives/partial/.+",
        "/var/cache/debconf/.+"
    ]
}
