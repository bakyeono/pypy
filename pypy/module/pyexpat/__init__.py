from pypy.interpreter.mixedmodule import MixedModule

class ErrorsModule(MixedModule):
    "Definition of pyexpat.errors module."
    appleveldefs = {}
    interpleveldefs = {}

    def setup_after_space_initialization(self):
        from pypy.module.pyexpat import interp_pyexpat
        space = self.space
        # Three mappings for errors: the module contains errors
        # message by symbol (errors.XML_ERROR_SYNTAX == 'syntax error'),
        # codes is a dict mapping messages to numeric codes
        # (errors.codes['syntax error'] == 2), and messages is a dict
        # mapping numeric codes to messages (messages[2] == 'syntax error').
        w_codes = space.newdict()
        w_messages = space.newdict()
        for name in interp_pyexpat.xml_error_list:
            w_name = space.wrap(name)
            num = getattr(interp_pyexpat, name)
            w_num = space.wrap(num)
            w_message = interp_pyexpat.ErrorString(space, num)
            space.setattr(self, w_name, w_message)
            space.setitem(w_codes, w_message, w_num)
            space.setitem(w_messages, w_num, w_message)
        space.setattr(self, space.wrap("codes"), w_codes)
        space.setattr(self, space.wrap("messages"), w_messages)

class ModelModule(MixedModule):
    "Definition of pyexpat.model module."
    appleveldefs = {}
    interpleveldefs = {}

    def setup_after_space_initialization(self):
        from pypy.module.pyexpat import interp_pyexpat
        space = self.space
        for name in interp_pyexpat.xml_model_list:
            value = getattr(interp_pyexpat, name)
            space.setattr(self, space.wrap(name), space.wrap(value))

class Module(MixedModule):
    "Python wrapper for Expat parser."

    appleveldefs = {
        }

    interpleveldefs = {
        'ParserCreate':  'interp_pyexpat.ParserCreate',
        'XMLParserType': 'interp_pyexpat.W_XMLParserType',
        'ErrorString':   'interp_pyexpat.ErrorString',

        'ExpatError':    'space.fromcache(interp_pyexpat.Cache).w_error',
        'error':         'space.fromcache(interp_pyexpat.Cache).w_error',

        '__version__':   'space.wrap("85819")',
        }

    submodules = {
        'errors': ErrorsModule,
        'model':  ModelModule,
    }

    for name in ['XML_PARAM_ENTITY_PARSING_NEVER',
                 'XML_PARAM_ENTITY_PARSING_UNLESS_STANDALONE',
                 'XML_PARAM_ENTITY_PARSING_ALWAYS']:
        interpleveldefs[name] = 'space.wrap(interp_pyexpat.%s)' % (name,)

    def startup(self, space):
        from pypy.module.pyexpat import interp_pyexpat
        w_ver = interp_pyexpat.get_expat_version(space)
        space.setattr(self, space.wrap("EXPAT_VERSION"), w_ver)
        w_ver = interp_pyexpat.get_expat_version_info(space)
        space.setattr(self, space.wrap("version_info"), w_ver)
