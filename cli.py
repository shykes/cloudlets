
import optparse

class CLIException(Exception):
    pass

class NotEnoughArgumentsError(CLIException):
    pass

class TooManyArgumentsError(CLIException):
    pass

class Option(dict):

    def __init__(self, arg, info):
        self.arg = arg
        self.info = info

    def get_valid(self):
        return self.info and type(self.info) in (list, tuple)
    valid = property(get_valid)

    def get_usage(self, long=False):
        usage = self.flags[-1] if long else self.flags[0]
        if self.metavar:
            usage = "%s%s%s" % (usage, "=" if long else " ", self.metavar)
        else:
            usage = self.flags[0]
            if self.optional:
                usage = "[%s]" % usage
        return usage
    usage = property(get_usage)

    def get_optional(self):
        return "default" in self.arg
    optional = property(get_optional)

    def get_default(self):
        return self.arg["default"]
    default = property(get_default)

    def get_flags(self):
        return list(self.info[0])
    flags = property(get_flags)

    def get_kw(self):
        kw = dict(zip(("help", "metavar"), self.info[1]))
        if self.optional and type(self.default) == bool:
            kw["default"] = self.default
            kw["action"] = "store_true"
        return kw
    kw = property(get_kw)

    def get_help(self):
        return self.kw.get("help")
    help = property(get_help)

    def get_metavar(self):
        return self.kw.get("metavar")
    metavar = property(get_metavar)


class Command(object):

    def __init__(self, fn, info):
        self.fn = fn
        self.info = info

    def get_opts(self):
        for arg in self.args:
            opt = Option(arg, self.info.get(arg["name"]))
            if not opt.valid:
                continue
            yield opt
    opts = property(get_opts)

    def get_values(self):
        for arg in self.args:
            if Option(arg, self.info.get(arg["name"])).valid:
                continue
            yield arg
    values = property(get_values)

    def get_args(self):
        args = [{"name": name} for name in self.fn.func_code.co_varnames[:self.fn.func_code.co_argcount]]
        for (arg, default) in zip(reversed(args), reversed(self.fn.func_defaults or [])):
            arg["default"] = default
        return args
    args = property(get_args)

    def get_parser(self):
        parser = optparse.OptionParser()
        for opt in self.opts:
            parser.add_option(*opt.flags, **opt.kw)
        return parser
    parser = property(get_parser)

    def get_min_values(self):
        return len([val for val in self.values if "default" not in val])
    min_values = property(get_min_values)

    def get_max_values(self):
        return len(self.args)
    max_values = property(get_max_values)

    def parse(self, args):
        (opts, values) = self.parser.parse_args(list(args))
        if len(values) < self.min_values:
            raise NotEnoughArgumentsError(self.usage)
        if len(values) > self.max_values:
            raise TooManyArgumentsError(self.usage)
        return (values, dict([(opt["name"], getattr(opts, opt["name"])) for opt in self.opts]))

    def get_name(self):
        return self.fn.func_name
    name = property(get_name)

    def get_usage(self, long=False):
        def lines():
            first_line = [self.name] + [opt.usage for opt in self.opts]
            for val in self.values:
                if "default" in val:
                    first_line.append("[%s]" % val["name"].upper())
                else:
                    first_line.append(val["name"].upper())
            yield " ".join(first_line)
            if not long:
                return
            yield ""
            for opt in self.opts:
                yield "\t" + ", ".join(opt.flags) + ("\t\t" + opt.help) if opt.help else ""
        return "\n".join(lines())
    usage = property(get_usage)

    def __call__(self, *args):
        (values, opts) = self.parse(args)
        return self.fn(*values, **opts)

def command(fn=None, **args_info):
    """ A decorator to wrap a CLI command around a function, using optparse.

    Examples:

        @command
        def foo(file):
            pass

        @command(file="Name of the file to load")
        def foo(file):
            pass

        @command(debug=(("-d", "--debug"), ("Enable debug mode")), file="Name of the file to load")
        def foo(file="default_filename", debug=True):
            pass
    """
    def decorator(fn):
        return Command(fn, args_info)
    if callable(fn):
        return decorator(fn)
    return decorator

def load(symbols=globals()):
    """ Return a dictionary of all CLI commands. Commands are created with the @command decorator. """
    return dict([(name, obj) for (name, obj) in symbols.items() if isinstance(obj, Command)])
