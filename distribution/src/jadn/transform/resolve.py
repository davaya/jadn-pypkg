import copy
import json
import os
from collections import defaultdict
from jadn.definitions import *
import jadn


class SchemaModule:
    def __init__(self, source):     # Read schema data, get module name
        self.source = None          # Filename or URL
        self.module = None          # Namespace unique name
        self.schema = None          # JADN data
        self.imports = None         # Copy of meta['imports'] or empty {}
        self.tx = None              # Type index: {type name: type definition in schema}
        self.deps = None            # Internal dependencies: {type1: {t2, t3}, type2: {t3, t4, t5}}
        self.refs = None            # External references {namespace1: {type1: {t2, t3}, ...}}
        self.used = None            # Types from this module that have been referenced {t2, t3}
        if isinstance(source, dict):    # If schema is provided, save data
            self.schema = source
        elif isinstance(source, str):   # If filename or URL is provided, load data and record source
            if '://' in source:
                pass                    # TODO: read schema from URL
            else:
                with open(source, encoding='utf-8') as f:
                    self.schema = json.load(f)
            self.source = source

        if 'meta' in self.schema:
            self.module = self.schema['meta']['module']
            self.imports = self.schema['meta']['imports'] if 'imports' in self.schema['meta'] else {}
        else:
            jadn.raise_error('Schema module must have a module ID')
        self.clear()

    def load(self):                 # Validate schema, build type dependencies and external references
        if not self.deps:           # Ignore if already loaded
            jadn.check(self.schema)
            self.tx = {t[TypeName]: t for t in self.schema['types']}
            self.deps = jadn.build_deps(self.schema)
            self.refs = defaultdict(lambda: defaultdict(set))
            for tn in self.deps:
                for dn in self.deps[tn].copy():     # Iterate over copy so original can be modified safely
                    if ':' in dn:
                        self.deps[tn].remove(dn)
                        nsid, typename = dn.split(':', maxsplit=1)
                        self.refs[self.imports[nsid]][tn].add(typename)

    def clear(self):
        self.used = set()

    def add_used(self, type):
        self.used.add(type)


def resolve_imports(schema, dirname, no_nsid=()):       # Add referenced types to schema. dirname => other schema files

    def merge_tname(tref, module, imports, nsids):
        """
        Convert reference to an imported type (nsid:TypeName) to a local type. Return unchanged if local.
        :param tref: Type name to be merged into the base module
        :param module: Namespace (unique name) of base module
        :param imports: Dict that maps base module's namespace ids to namespaces
        :param nsids: Dict that maps each namespace to a namespace id. If blank, do not append $nsid qualifier
        :return: Local type name, qualified (TypeName$nsid) or unqualified (TypeName)
        """

        sys = '$'  # Character reserved for use in tool-generated type names
        nsid, tname = tref.split(':', maxsplit=1) if ':' in tref else ('', tref)
        ns_id = nsids[imports[nsid] if nsid else module][0]
        return tname + sys + ns_id if ns_id and not is_builtin(tname) else tname

    def merge_typedef(tdef, module, imports, nsids):
        def update_opts(opts):
            return [x[0] + merge_tname(x[1:], module, imports, nsids) if x[0] in oids else x for x in opts]

        oids = [OPTION_ID['ktype'], OPTION_ID['vtype'], OPTION_ID['and']]  # Options whose value is/has a type name
        tn = merge_tname(tdef[TypeName], module, imports, nsids)
        td = [tn, tdef[BaseType], tdef[TypeOptions], tdef[TypeDesc]]
        td[TypeOptions] = update_opts(td[TypeOptions])
        if len(tdef) > Fields:
            new_fields = copy.deepcopy(tdef[Fields])
            if td[BaseType] != 'Enumerated':
                for f in new_fields:
                    f[FieldOptions] = update_opts(f[FieldOptions])
                    f[FieldType] = merge_tname(f[FieldType], module, imports, nsids)
            td.append(new_fields)
        return td

    def make_enum(sm, tname):
        if tname[0] in (OPTION_ID['enum'], OPTION_ID['pointer']):
            sys = '$'
            tn = tname[1:]
            if tn not in sm.used and tn in sm.tx:
                if tname[0] == OPTION_ID['enum']:
                    print('  Make enum', tname)
                    edef = [tn + sys + 'Enum', 'Enumerated', [], '', [[f[0], f[1], ''] for f in sm.tx[tn][Fields]]]
                else:
                    print('  Make pointers', tname)
                    edef = [tn + sys + 'Point', 'Enumerated', [], '', [[f[0], f[1], ''] for f in sm.tx[tn][Fields]]]
                sm.schema['types'].append(edef)
            return(True)

    def add_types(sm, tname):        # add referenced typenames in this module to used list
        if {tname} - sm.used:
            sm.add_used(tname)
            try:
                [add_types(sm, tn) for tn in sm.deps[tname]]
            except KeyError as e:
                if not make_enum(sm, tname):
                    print('Error:', e, 'not defined in', sm.module, '(' + sm.source + ')')

    def resolve(sm, types):       # add referenced types from other modules to used list
        if set(types) - sm.used:
            sm.load()
            [add_types(sm, tn) for tn in types]
            for mod in sm.refs:
                if mod in modules:
                    resolve(modules[mod], {t for k, v in sm.refs[mod].items() if k in sm.used for t in v})
                    print('  Merge', mod, 'into', sm.module)
                else:
                    print('Error: module', mod, 'not found.')

    # if 'imports' not in schema['meta']:
    #    return schema
    root = SchemaModule(schema)
    modules = {root.module: root}
    nsids = defaultdict(list)
    for fn in (os.path.join(dirname, f) for f in os.listdir(dirname) if os.path.splitext(f)[1] == '.jadn'):
        sm = SchemaModule(fn)
        if sm.module not in modules:            # Add new module to list
            modules.update({sm.module: sm})
        elif root.module == sm.module and root.schema == sm.schema:     # Update source of root schema if found
            modules[sm.module].source = fn
        elif sm.source != fn:                   # Flag multiple files with same module name
            print('* Duplicate module', sm.module, sm.source, 'Ignoring', fn)
        for id, m in sm.imports.items():
            nsids[m].append('' if id in no_nsid else id)
    types = root.schema['meta']['exports'] if 'exports' in root.schema['meta'] else {}
    resolve(root, types)

    for t in root.used.copy():
        if t[0] in (OPTION_ID['enum'], OPTION_ID['pointer']):
            if t[1:] in root.used:
                root.used.remove(t)     # Don't need explicit type if base type is present
            else:
                print('  Error: no base type for', t)


    # Copy all needed types from other modules into root
    nsids[root.module] = ['']
    sc = {'meta': {k: v for k, v in root.schema['meta'].items() if k != 'imports'}, 'types': []}    # Remove imports
    for sm in [root] + [m for m in modules.values() if m.module != root.module]:
        sc['types'] += [merge_typedef(t, sm.module, sm.imports, nsids) for t in sm.schema['types'] if t[TypeName] in sm.used]
    return sc
