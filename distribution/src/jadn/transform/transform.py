import copy
from jadn.definitions import *
from jadn import topts_s2d, ftopts_s2d, opts_d2s, get_optx, del_opt


def strip_comments(schema, width=0):             # Strip or truncate comments from schema
    def estrip(s, n):
        return s[:n-2] + (s[n-2:], '..')[len(s) > n] if n > 1 else s[:n]

    sc = copy.deepcopy(schema)
    for tdef in sc['types']:
        tdef[TypeDesc] = estrip(tdef[TypeDesc], width)
        if len(tdef) > Fields:
            fd = ItemDesc if tdef[BaseType] == 'Enumerated' else FieldDesc
            for fdef in tdef[Fields]:
                fdef[fd] = estrip(fdef[fd], width)
    return sc


def simplify(schema, extensions=EXTENSIONS):      # Remove schema extensions
    """
    Given an input schema, return a simplified schema with some or all extensions removed.

    extensions = set of extension names to process:
        AnonymousType:   Replace all anonymous type definitions with explicit
        Multiplicity:    Replace all multi-value fields with explicit ArrayOf type definitions
        DerivedEnum:     Replace all derived and pointer enumerations with explicit Enumerated type definitions
        MapOfEnum:       Replace all MapOf types with listed keys with explicit Map type definitions
    """

    def epx(topts):             # Return option array index of enum or pointer option
        ex = get_optx(topts, 'enum')
        px = get_optx(topts, 'pointer')
        return ex if ex is not None else px

    def epname(topts):
        x = epx(topts)
        if x is not None:
            oname = 'Enum' if topts[x][0] == OPTION_ID['enum'] else 'Pointer'
            return topts[x][1:] + sys + oname + ('-Id' if get_optx(topts, 'id') else '')

    def simplify_multiplicity():            # Replace field multiplicity with explicit ArrayOf type definitions
        new_types = []
        for tdef in tdefs:
            if has_fields(tdef[BaseType]):
                for fdef in tdef[Fields]:
                    fo, fto = ftopts_s2d(fdef[FieldOptions])
                    if ('maxc' in fo and fo['maxc'] != 1):
                        newname = tdef[TypeName] + sys + fdef[FieldName]
                        minc = fo['minc'] if 'minc' in fo else 1
                        newopts = {'vtype': fdef[FieldType], 'minv': max(minc, 1)}      # Don't allow empty ArrayOf
                        newopts.update({'maxv': fo['maxc']} if fo['maxc'] > 1 else {})  # maxv defaults to 0
                        newopts.update({'unique': True} if 'unique' in fto else {})     # Move unique option to ArrayOf
                        new_types.append([newname, 'ArrayOf', opts_d2s(newopts), fdef[FieldDesc], []])
                        fdef[FieldType] = newname   # Point existing field to new ArrayOf
                        f = fdef[FieldOptions]      # Remove unused FieldOptions
                        del_opt(f, 'maxc')
                        if minc != 0:
                            del_opt(f, 'minc')
                        del_opt(f, 'unique')
        return new_types

    def simplify_anonymous_types():          # Replace anonymous types in fields with explicit type definitions
        new_types = []
        for tdef in tdefs:
            if has_fields(tdef[BaseType]):
                for fdef in tdef[Fields]:
                    fo, fto = ftopts_s2d(fdef[FieldOptions])
                    if fto:                 # If FieldOptions contains a type option, create an explicit type
                        newopts = []
                        for o in fto:       # Move all type options to new type
                            newopts.append(fdef[FieldOptions].pop(get_optx(fdef[FieldOptions], o)))
                        name = epname(newopts)              # If enum/pointer option, use derived enum typename
                        newname = name if name else tdef[TypeName] + sys + fdef[FieldName]
                        if newname not in [t[TypeName] for t in new_types]:
                            newtype = 'Enumerated' if epx(newopts) is not None else fdef[FieldType]
                            assert is_builtin(newtype)      # Don't create a bad type definition
                            new_types.append([newname, newtype, newopts, fdef[FieldDesc], []])
                        fdef[FieldType] = newname           # Redirect field to explicit type definition
        return new_types

    def simplify_derived_enum():             # Generate Enumerated list of fields or JSON Pointers
        def update_eref(enums, opts, optname, new):
            n = get_optx(opts, optname)
            if n is not None:
                name = epname([opts[n][1:]])
                if name:
                    if name in enums:       # Reference existing Enumerated type
                        opts[n] = opts[n][:1] + enums[name]
                    else:                   # Make new Enumerated type
                        make_items = enum_items if opts[n][1:2] == OPTION_ID['enum'] else pointer_items
                        opts[n] = opts[n][:1] + name
                        new.append([name, 'Enumerated', [], '', make_items(name.split(sys)[0])])

        def enum_items(rtype):
            tdef = tdefs[typex[rtype]]
            fields = tdef[Fields] if has_fields(tdef[BaseType]) else []
            return [[f[FieldID], f[FieldName], f[FieldDesc]] for f in fields]

        def pointer_items(rtype):
            def pathnames(rtype, base=''):                   # Walk subfields of referenced type
                tdef = tdefs[typex[rtype]]
                if has_fields(tdef[BaseType]):
                    for f in tdef[Fields]:
                        if OPTION_ID['dir'] in f[FieldOptions]:
                            yield from pathnames(f[FieldType], f[FieldName] + '/')
                        else:
                            yield [base + f[FieldName], f[FieldDesc]]
            return [[n+1] + f for n, f in enumerate(pathnames(rtype))]

        enums = {}
        for tdef in tdefs:              # Replace enum/pointer options in Enumerated types with explicit items
            if tdef[BaseType] == 'Enumerated':
                to = tdef[TypeOptions]
                rname = epname(to)
                if rname:
                    optx = get_optx(to, 'enum')
                    optx = optx if optx is not None else get_optx(to, 'pointer')
                    items = enum_items if to[optx][:1] == OPTION_ID['enum'] else pointer_items
                    tdef[Fields] = items(to[optx][1:])
                    del to[optx]
                    enums.update({rname: tdef[TypeName]})
        new_types = []                  # Create new Enumerated enum/pointer types if they don't already exist
        for tdef in tdefs:
            if tdef[BaseType] in ('ArrayOf', 'MapOf'):
                update_eref(enums, tdef[TypeOptions], 'vtype', new_types)
                update_eref(enums, tdef[TypeOptions], 'ktype', new_types)
        return new_types

    def simplify_map_of_enum():           # Replace MapOf(enumerated key) with explicit Map
        for n, tdef in enumerate(tdefs):
            to = topts_s2d(tdef[TypeOptions])
            if tdef[BaseType] == 'MapOf' and tdefs[typex[to['ktype']]][BaseType] == 'Enumerated':
                newfields = [[f[ItemID], f[ItemValue], to['vtype'], [], f[ItemDesc]] for f in tdefs[typex[to['ktype']]][Fields]]
                tdefs[n] = [tdef[TypeName], 'Map', [], tdef[TypeDesc], newfields]

    assert extensions - EXTENSIONS == set()
    sys = '$'                                   # Character reserved for tool-generated TypeNames
    sc = copy.deepcopy(schema)                  # Don't modify original schema
    tdefs = sc['types']
    if 'Multiplicity' in extensions:            # Expand repeated types into ArrayOf defintions
        tdefs += simplify_multiplicity()
    if 'AnonymousType' in extensions:           # Expand inline definitions into named type definitions
        tdefs += simplify_anonymous_types()
    typex = {t[TypeName]: n for n, t in enumerate(tdefs)}       # Build type index
    if 'DerivedEnum' in extensions:             # Generate Enumerated list of fields or JSON Pointers
        tdefs += simplify_derived_enum()
    if 'MapOfEnum' in extensions:               # Generate explicit Map from MapOf
        simplify_map_of_enum()
    return sc


def get_enum_items(tdef, topts, types):
    def ptr(fdef):
        if OPTION_ID['dir'] in fdef[FieldOptions]:
            return fdef[FieldName] + "^"
        return fdef[FieldName]

    if 'enum' in topts:
        return types[topts['enum']][Fields]
    elif 'pointer' in topts:
        return [(n, ptr(f), '') for n, f in enumerate(types[topts['pointer']][Fields])]
    return tdef[Fields]
