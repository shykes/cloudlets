cloudlets v.0.0.2

Author: Solomon Hykes <solomon.hykes@dotcloud.com>
License : see LICENSE file.
Url: http://bitbucket.org/dotcloud/cloudlets

Description:
------------

Cloudlets are universal server images for the cloud.

They're lightweight, version-controlled, and you can export them to any bootable format known to man: Xen, KVM, Amazon EC2, or just a plain bootable CD.


Example:
--------

For now you can only configure cloudlet images in-place.
If you want to keep an unconfigured master, it's up to you to create copies with rsync or aufs.


1. Copy your image to keep an unconfigured copy

# cp -R sample.cloudlet host1.cloudlet


2. Configure the image

# cloudlets config host1.cloudlet '{"args": {"hostname": "host1"}, "dns": {"nameservers": ["0.0.0.0"]}, "ip": {"interfaces": []}}'


3. Your image is now a configured and bootable filesystem!

# chroot host1.cloudlet


Coming soon:
------------

 * Distributed versioning (fork and improve other people's images!)
 * Multi-image stacks
 * Automated tests (Cucumber tests for your stack!)
 * VM generator

And much more.
