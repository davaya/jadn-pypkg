import copy
import json
import os

from collections import defaultdict
from typing import Dict, Optional, List, NoReturn, Set, Tuple, Union
from ..core import check
from ..definitions import (
    TypeName, BaseType, TypeOptions, TypeDesc, Fields, FieldType, FieldOptions, OPTION_ID, is_builtin
)
from ..utils import build_deps, raise_error


class SchemaModule:
    source: Optional[str]                 # Filename or URL
    module: str                           # Namespace unique name
    schema: dict                          # JADN data
    imports: dict                         # Copy of meta['imports'] or empty {}
    tx: Dict[str, list]                   # Type index: {type name: type definition in schema}
    deps: Dict[str, List[str]]            # Internal dependencies: {type1: {t2, t3}, type2: {t3, t4, t5}}
    refs: Dict[str, Dict[str, Set[str]]]  # External references {namespace1: {type1: {t2, t3}, ...}}
    used: Set[str]                        # Types from this module that have been referenced {t2, t3}

    def __init__(self, source: Union[dict, str]):     # Read schema data, get module name
        if isinstance(source, dict):    # If schema is provided, save data
            self.schema = source
        elif isinstance(source, str):   # If filename or URL is provided, load data and record source
            if '://' in source:
                pass                    # TODO: read schema from URL
            else:
                with open(source, encoding='utf-8') as f:
                    try:
                        self.schema = json.load(f)
                    except json.JSONDecodeError:
                        print("Decoding", source)
                        raise
            self.source = source

        try:
            self.module = self.schema['info']['module']
            self.imports = self.schema['info']['imports'] if 'imports' in self.schema['info'] else {}
        except KeyError:
            raise_error(f'Schema module {self.source} must have a module ID')
        self.clear()

    def load(self) -> NoReturn:     # Validate schema, build type dependencies and external references
        if not self.deps:           # Ignore if already loaded
            check(self.schema)
            self.tx = {t[TypeName]: t for t in self.schema['types']}
            self.deps = build_deps(self.schema)
            self.refs = defaultdict(lambda: defaultdict(set))
            for tn in self.deps:
                for dn in self.deps[tn].copy():     # Iterate over copy so original can be modified safely
                    if ':' in dn:
                        self.deps[tn].remove(dn)
                        nsid, typename = dn.split(':', maxsplit=1)
                        try:
                            self.refs[self.imports[nsid]][tn].add(typename)
                        except KeyError as e:
                            raise_error(f'Resolve: no namespace defined for {e}')

    def clear(self) -> NoReturn:
        self.used = set()

    def add_used(self, t) -> NoReturn:
        self.used.add(t)


# Resolve util functions
def merge_tname(tref: str, module: str, imports: Dict[str, str], nsids: dict, sys: str = '$') -> str:
    """
    Convert reference to an imported type (nsid:TypeName) to a local type. Return unchanged if local.
    :param tref: Type name to be merged into the base module
    :param module: Namespace (unique name) of base module
    :param imports: Dict that maps base module's namespace ids to namespaces
    :param nsids: Dict that maps each namespace to a namespace id. If blank, do not append $nsid qualifier
    :param sys: single character system generated type delimiter
    :return: Local type name, qualified (TypeName$nsid) or unqualified (TypeName)
    """
    nsid, tname = tref.split(':', maxsplit=1) if ':' in tref else ('', tref)
    ns_id = nsids[imports[nsid] if nsid else module][0]
    return f'{tname}{sys}{ns_id}' if ns_id and not is_builtin(tname) else tname


def merge_typedef(tdef: list, module: str, imports: Dict[str, str], nsids: dict, sys: str = '$') -> list:
    def update_opts(opts: List[str]) -> List[str]:
        return [x[0] + merge_tname(x[1:], module, imports, nsids, sys) if x[0] in oids else x for x in opts]

    oids = [OPTION_ID['ktype'], OPTION_ID['vtype'], OPTION_ID['and']]  # Options whose value is/has a type name
    tn = merge_tname(tdef[TypeName], module, imports, nsids, sys)
    td = [tn, tdef[BaseType], update_opts(tdef[TypeOptions]), tdef[TypeDesc]]
    if len(tdef) > Fields:
        new_fields = copy.deepcopy(tdef[Fields])
        if td[BaseType] != 'Enumerated':
            for f in new_fields:
                f[FieldOptions] = update_opts(f[FieldOptions])
                f[FieldType] = merge_tname(f[FieldType], module, imports, nsids, sys)
        td.append(new_fields)
    return td


def make_enum(sm: SchemaModule, tname: str, sys: str = '$') -> bool:
    if tname[0] in (OPTION_ID['enum'], OPTION_ID['pointer']):
        tn = tname[1:]
        if tn not in sm.used and tn in sm.tx:
            etype = 'Enum' if tname[0] == OPTION_ID['enum'] else 'Point'
            edef = [f'{tn}{sys}{etype}', 'Enumerated', [], '', [[f[0], f[1], ''] for f in sm.tx[tn][Fields]]]
            sm.schema['types'].append(edef)
        return True
    return False


def add_types(sm: SchemaModule, tname: str, sys: str = '$') -> NoReturn:  # add referenced typenames in this module to used list
    if {tname} - sm.used:
        sm.add_used(tname)
        try:
            for tn in sm.deps[tname]:
                add_types(sm, tn)
        except KeyError as e:
            if not make_enum(sm, tname, sys):
                raise_error(f'Resolve: {e} not defined in {sm.module} ({sm.source})')


def resolve(sm: SchemaModule, types: Set[str], modules: dict, sys: str = '$') -> NoReturn:  # add referenced types from other modules to used list
    if set(types) - sm.used:
        sm.load()
        for tn in types:
            add_types(sm, tn, sys)
        for mod in sm.refs:
            if mod in modules:
                resolve(modules[mod], {t for k, v in sm.refs[mod].items() if k in sm.used for t in v}, modules)
                print(f'  Resolve {mod} into {sm.module}')
            else:
                raise_error('Resolve: module', mod, 'not found.')


# Add referenced types to schema. dirname => other schema files
def resolve_imports(schema: dict, dirname: str, no_nsid: Tuple[str, ...] = ()):
    sys = '$'  # Character reserved for use in tool-generated type names
    # if 'imports' not in schema['info']:
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
        for i, m in sm.imports.items():
            nsids[m].append('' if i in no_nsid else i)
    resolve(root, root.schema['info']['exports'] if 'exports' in root.schema['info'] else set(), modules)

    for t in root.used.copy():
        if t[0] in (OPTION_ID['enum'], OPTION_ID['pointer']):
            if t[1:] not in root.used:
                raise_error(f'Resolve: no base type for {t}')
            root.used.remove(t)     # Don't need explicit type if base type is present

    # Copy all needed types from other modules into root
    nsids[root.module] = ['']
    sc = {'info': {k: v for k, v in root.schema['info'].items() if k != 'imports'}, 'types': []}    # Remove imports
    for sm in [root] + [m for m in modules.values() if m.module != root.module]:
        sc['types'] += [merge_typedef(t, sm.module, sm.imports, nsids, sys) for t in sm.schema['types'] if t[TypeName] in sm.used]
    return sc
