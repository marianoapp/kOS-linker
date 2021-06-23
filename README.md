kOS linker
==========

Statically link a script and it's library dependencies into a single file.
It scans the file and imports only the functions used from the library. This process is recursive and follows the library's dependencies too.

## Requirements
Python 3

## Usage
`linker.py file`

## Notes
Currently only support libraries that conform with the following format
```
global [library name] to ({
    
    [local functions]
    
    return lex(
        [export of local functions]
    ).
}):call().
```

## Example
Let's define a sample library
```
global sampleLib to ({
    local function functionA {
        return "A".
    }

    local function functionB {
        return "B".
    }
    
    return lex(
        "functionA", functionA@,
        "functionB", functionB@
    ).
}):call().
```

Which is used like this
```
runoncepath("/lib/sampleLib").

print sampleLib:functionA().
```

And the result after being linked would be
```
local function sampleLib_functionA {
    return "A".
}

print sampleLib_functionA().
```