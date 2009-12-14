clapp v.0.0.1

Author: Solomon Hykes <solomon.hykes@dotcloud.com>
License : see LICENSE file.
Url: http://bitbucket.org/dotcloud/clapp

Description:
------------
clapp (Cloud Layered Appliance) is a master format for server images.

It's small, it's simple, it's version-controlled, and you can compile it
to any bootable format known to man: Xen, KVM, AMI, or just a plain bootable CD.


Example:
--------

For now clapp can only do one thing: configure an image in-place.
If you want to keep an unconfigured master,
it's up to you to create copies with rsync or aufs.

# cp -R sample.clapp host1.clapp
# python clapp.py host1.clapp '{"hostname": "host1"}'
# cat host1.clapp/etc/hostname

