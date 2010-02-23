
from unittest import TestCase
import cloudlets


class TestSchema(TestCase):

    def test_a(self):
        input = {"foo": {"type": "string"}, "bar": {"type": "string"}}
        self.assertEqual(cloudlets.DictSchema(input), {"type": "object", "properties": input})

    def test_validate_default_used(self):
        input = {"foo": {"type": "string", "default": "abc"}}
        self.assertEqual(cloudlets.DictSchema(input).validate({}), {"foo": "abc"})

    def test_validate_default_not_used(self):
        input = {"foo": {"type": "string", "default": "abc"}}
        self.assertEqual(cloudlets.DictSchema(input).validate({"foo": "bar"}), {"foo": "bar"})

    def test_validate_no_default(self):
        input = {"foo": {"type": "string"}}
        self.assertEqual(cloudlets.DictSchema(input).validate({"foo": "bar"}), {"foo": "bar"})

    def test_noop(self):
        schema = {"type": "string", "optional": True}
        self.assertEqual(cloudlets.DictSchema(schema), schema)

class TestManifest(TestCase):

    manifest_min = cloudlets.Manifest({
                "arch"      : "i386",
                "volatile"  : []
            })

    manifest_simple_args = cloudlets.Manifest(manifest_min,
            args = {"hostname": {"type": "string", "default": "noname"}}
            )
    

    def test_smallest_possible(self):
        self.manifest_min.validate()

    def test_args_schema(self):
        self.assertEqual(self.manifest_simple_args.args_schema.validate({"hostname": "foo"}), {"hostname": "foo"})
        self.assertEqual(self.manifest_simple_args.args_schema.validate({}), {"hostname": "noname"})

    def test_config_schema(self):
        config_in  = {"dns": {"nameservers": []}, "ip": {"interfaces": []}, "args": {}}
        config_out = {"dns": {"nameservers": []}, "ip": {"interfaces": []}, "args": {"hostname": "noname"}}
        self.assertEqual(self.manifest_simple_args.config_schema.validate(config_in), config_out)

    def test_defaults(self):
        self.assertEqual(self.manifest_min.validate()["templates"], [])
        self.assertEqual(self.manifest_min.validate()["persistent"], [])
