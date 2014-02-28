"""
Functions to take a list of C-style function prototypes and output
ctypes-based bindings for those functions.

Only type information (and optional annotations as below) will be parsed.
Note that 'extern', pre-processor macros, typedefs, struct definitions and 
anything other than bare function prototypes cannot be parsed. Any 'const'
keywords will be stripped and ignored, so beware.

Output functions have helpful docstrings, and arguments can be called by name
or position as usual with python functions.

This library can deal with C base types. Any typedefs, structs, and similar
must be defined separately and passed in as an 'additional_definitions' dict.

For example, if ARRAY_T is a typedef for void * and acts as an opaque type, 
the annotated function prototype:
ARRAY_T subarray(ARRAY_T input, int start, int_end);
will parse properly only if an additional_definitions parameter of:
{'ARRAY_T': ctypes.c_void_p}
Note that the locals() dict can be used for clean method definitions.

This library can create pointers to base and defined types as required, so it
knows how to deal with 'int **' or 'ARRAY_T *' if ARRAY_T is defined as above.

Arguments in functon prototypes can be annotated with a trailing '[output]' to
indicate that they are pointers passed in by reference and filled in by the 
function. The parmeters marked as output do not need to be provided to the
python call of the function, and the value of the pointer for output 
parameter(s) will be returned in a tuple following the function's return
value, if any. (If there is only one return value and/or output parameter,
only a single value will be returned, not wrapped in a tuple.)

Any more complicated style of output parameter must be dealt with by the
caller.

Functions can be annotated as well with a python "error check" function to
call. For details, see the ctypes documentation about the "errcheck" function.
Note that with output parameters, the errcheck function is passed the pointer;
if the value of the pointer is needed for the output it must be explicitly
accessed (unlike without error check functions, where these values are
automatically unwraped). See below for an example of this. Note that the
errcheck function's docstring, if any, will be used to annotate the function
output.

Example usage, with an example C library for manipulating arrays:

import ctypes
import generate_ctypes

protos = '''
  int [check_error] make_array(ARRAY_T *array [output], int size_requested);
  ARRAY_T subarray(ARRAY_T input, int start, int_end);
'''
ARRAY_T = ctypes.c_void_p
def check_error(result, func, arguments):
    '''Returns: ARRAY_T'''
    array_t_ptr, size_requested = arguments
    if result != size_requested:
        raise RuntimeError('Array library could not create array.')
    return result, array_t_ptr.value
    
array_library = ctypes.CDLL('/path/to/libarray.so')
generate_ctypes.process_prototypes(protos.strip().split('\\n'), array_library, 
    additional_definitions=locals())

size_allocated, array = array_library.make_array(20)
slice = array_library.subarray(array, end=12, start=5)

TODO: ctypes paramflags allows for providing default arguments to parameters.
Could add syntax for default value handling.

"""

import ctypes
import pyparsing

# Crappy BNF grammar for annotated C prototypes
# <identifier> ::= _a-zA-Z[_a-zA-Z0-9]*   -- variable or type name
# <type keyword> ::= const | void | char | short | int | long | float | double | signed | unsigned
# <type declarator> ::= (<type keyword>+ | <identifier>) <pointer>?  -- type defintion with optional pointer specification, allows for multiple keywords like 'unsigned long int'
# <pointer> ::= * const <pointer>? -- one or more *s for levels of pointer
# <argument declarator> ::= <type declarator> <identifier> <intent>? -- arguments with optional intent annotation
# <intent> ::= [output] -- intent can be declared as an 'output-only' variable passed by reference
# <function declarator> ::= <type declarator> <identifier> <error checker>? -- function defintion with optional error checker name
# <error checker> ::= [<identifier>] -- error checker is a python identifier to decorate the function with
# <function prototype> ::= <error checker> ( {<variable declarator>,}* <variable declarator>? );?

identifier = pyparsing.Word(pyparsing.alphas+"_", pyparsing.alphanums+"_" )
_const = pyparsing.Suppress(pyparsing.Keyword('const'))
_lpar, _rpar, _lbrk, _rbrk, _semi = map(pyparsing.Suppress, '()[];')
pointer = pyparsing.Forward()
pointer << '*' + pyparsing.Optional(_const) + pyparsing.Optional(pointer)
type_keyword = _const ^ pyparsing.Or([pyparsing.Keyword(k) for k in 'void char short int long float double signed unsigned'.split()])
type_decl = pyparsing.Group(pyparsing.Group(pyparsing.OneOrMore(type_keyword) ^ identifier) + pyparsing.Optional(pointer))
intent = _lbrk + pyparsing.Keyword('output') + _rbrk
arg_decl = pyparsing.Group(type_decl + identifier + pyparsing.Optional(intent))
error_check = _lbrk + identifier + _rbrk
function_decl = pyparsing.Group(type_decl + pyparsing.Optional(error_check) + identifier)
function_prototype = ( function_decl + _lpar +
    pyparsing.Group(pyparsing.Optional(pyparsing.delimitedList(arg_decl, ',')))  + 
    _rpar + pyparsing.Optional(_semi) )

base_types = {
    'bool': ctypes.c_bool,
    'char': ctypes.c_char,
    'char *': ctypes.c_char_p,
    'double': ctypes.c_double,
    'float': ctypes.c_float,
    'int': ctypes.c_int,
    'int16': ctypes.c_int16,
    'int32': ctypes.c_int32,
    'int64': ctypes.c_int64,
    'int8': ctypes.c_int8,
    'long': ctypes.c_long,
    'long int': ctypes.c_long,
    'long double': ctypes.c_longdouble,
    'long long': ctypes.c_longlong,
    'long long int': ctypes.c_longlong,
    'short': ctypes.c_short,
    'short int': ctypes.c_short,
    'size_t': ctypes.c_size_t,
    'ssize_t': ctypes.c_ssize_t,
    'unsigned int': ctypes.c_uint,
    'unsigned int16': ctypes.c_uint16,
    'unsigned int32': ctypes.c_uint32,
    'unsigned int64': ctypes.c_uint64,
    'unsigned int8': ctypes.c_uint8,
    'uint': ctypes.c_uint,
    'uint16': ctypes.c_uint16,
    'uint32': ctypes.c_uint32,
    'uint64': ctypes.c_uint64,
    'uint8': ctypes.c_uint8,
    'unsigned long': ctypes.c_ulong,
    'unsigned long int': ctypes.c_ulong,
    'unsigned long long': ctypes.c_ulonglong,
    'unsigned long long int': ctypes.c_ulonglong,
    'unsigned short': ctypes.c_ushort,
    'unsigned short int': ctypes.c_ushort,
    'void *': ctypes.c_void_p,
    'wchar': ctypes.c_wchar,
    'wchar *': ctypes.c_wchar_p,
    'void': None
}

def process_prototypes(prototypes, library, additional_definitions={}):
    """Given a list of annotated C function prototypes (see module docstring),
    for syntax), a ctypes library, and an optional dict of non-base type
    definitions, load those functions from the library with proper 
    type-checking, and make them available as attributes of the library."""
    
    for prototype in prototypes:
        function_name, library_function = create_library_prototype(prototype, library, additional_definitions)
        setattr(library, function_name, library_function)

def create_library_prototype(prototype, library, additional_definitions={}):
    """Given a single annotated C function prototypes (see module docstring),
    for syntax), a ctypes library, and an optional dict of non-base type
    definitions, load that function from the library with proper 
    type-checking and return the function."""
    
    function_name, return_type, arg_types, param_flags, errcheck, docstring = parse_prototype(prototype, additional_definitions)
    prototype = ctypes.CFUNCTYPE(return_type, *arg_types)
    library_function = prototype((function_name, library), param_flags)
    if errcheck:
        library_function.errcheck = errcheck
    library_function.__doc__ = docstring
    return function_name, library_function

def parse_prototype(prototype, additional_definitions={}):
    """Given a single annotated C function prototypes (see module docstring),
    for syntax), and an optional dict of non-base type definitions,
    return the following information that ctypes needs to load and annotate
    a function:
    function_name: str
    return_type: ctypes type
    arg_types: tuple of ctypes types
    param_flags: tuple same length of arg_types with (arg_intent, arg_name)
        values (see ctypes documentation for 'paramflags')
    errcheck: errcheck function (if provided via annotation, or if necessary
        to pack up output args and return values)
    docstring: auto-generated docstring for the function.
    """

    results = function_prototype.parseString(prototype)
    function_decl = results[0]
    args = results[1]
    
    #deal with the return type and error check function if present
    return_type, function_name = function_decl[0], function_decl[-1]
    py_return_type = resolve_type(return_type, additional_definitions)
    errcheck = None
    if len(function_decl) == 3:
        errcheck = additional_definitions[function_decl[1]]
    
    # process the arguments 
    arg_types, param_flags = [], []
    in_args, out_args = [], []
    for i, arg in enumerate(args):
        arg_type, arg_name = arg[:2]
        py_arg_type = resolve_type(arg_type, additional_definitions)
        arg_types.append(py_arg_type)
        if len(arg) == 3 and arg[2] == 'output':
            param_intent = 2 # ctypes flag for 'output' parameter
            out_args.append(i)
        else:
            param_intent = 1 # ctypes flag for 'input' parameter
            in_args.append(i)
        param_flags.append((param_intent, arg_name))

    docstring = construct_docstring(function_name, errcheck, arg_types, param_flags, in_args, out_args, py_return_type)

    # deal with possibility of multiple outputs
    if out_args and py_return_type is not None and not errcheck:
        # if we have both pass-by-reference output arguments and a non-void return type,
        # AND if there's no custom error check function, we need to make our
        # own to bundle all the output arguments
        def errcheck(result, func, arguments):
            return (result,) + tuple(arguments[i].value for i in out_args)
                           
    return function_name, py_return_type, tuple(arg_types), tuple(param_flags), errcheck, docstring

def resolve_type(parsed_type, additional_definitions):
    """Resolve the c type definition into either a cython base type or a type
    defined by the user in additional_definitions (with pointers automatically
    added as necessary).
    """
    
    base_type = parsed_type[0]
    pointers = len(parsed_type[1:])
    if len(base_type) > 1:
        # if we have a multi-word base type, turn it back to a string
        base_type = ' '.join(base_type)
    else:
        # otherwise just grab the string from the one-element list
        base_type = base_type[0]
    
    py_type = None
    if pointers:
        # ctypes has special names for some basic pointer types like
        # void * and char *, etc., so try to look that up first -- especially
        # important because ctypes.c_char_p doesn't behave exactly like
        # ctypes.POINTER(ctypes.c_char)
        ptr_name = base_type + ' *'
        if ptr_name in base_types:
            py_type = base_types[ptr_name]
            lookup_done = True
            pointers -= 1  
    
    if not py_type:
        try:
            py_type = base_types[base_type]
        except KeyError:
            py_type = additional_definitions[base_type]
    for i in range(pointers):
        py_type = ctypes.POINTER(py_type)
    return py_type

def construct_docstring(function_name, errcheck, arg_types, param_flags, in_args, out_args, py_return_type):
    """Construct a docstring based on parsed-out function data and the
    resolved python types."""
    
    if errcheck:
        if errcheck.__doc__:
            docstring_out = [errcheck.__doc__.strip()]
        else:
            docstring_out = ['']
    else:
        return_repr = py_return_type.__name__
        outputs = []
        if out_args:
            if  py_return_type is not None:
                # some arguments are outputs AND there is a return value
                docstring_out = ['Returns a tuple of:', 'return-value: ' + return_repr]
            elif len(out_args) == 1:
                # only output is a single output argument
                docstring_out = ['Returns: ' + arg_types[out_args[0]].__name__]
            else:
                # must be multiple output args
                docstring_out = ['Returns a tuple of:']
            for i in out_args:
                arg_name = param_flags[i][1]
                arg_type = arg_types[i]._type_.__name__
                docstring_out.append(arg_name + ': '+arg_type)
        else:
            # only output is the return value
            docstring_out = ['Returns: ' + return_repr]
    
    docstring_in = ['Input parameters:']
    for i in in_args:
        arg_name = param_flags[i][1]
        arg_type = arg_types[i].__name__
        docstring_in.append(arg_name + ': '+arg_type)
    docstring_in.append('')
    docstring = '\n'.join([function_name, '-'*len(function_name), '']+ docstring_in + docstring_out)
    return docstring
