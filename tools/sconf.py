# Custom checks

def ConfigureWX(context, version, libs='', wx_config='wx-config', wx_flags='', wx_debug=False):
    """ Configure wxWidgets and set the flags as needed """

    # Check for wx-config if needed
    if not wx_flags:
        context.Message('Checking for wx-config... ')
        ret = context.TryAction(wx_config + ' --release')[0]
        context.Result(ret)
        if not ret:
            return False

        # Get flags from wx-config
        if wx_debug:
            flags = ' --debug'
        else:
            flags = ''

        if libs:
            flags = libs + flags

        context.env.ParseConfig(wx_config + ' --cxxflags --libs' + flags)
    else:
        context.env.MergeFlags(wx_flags)

    # Check for the version number
    context.Message('Checking for wxWidgets >= %s... ' % version)
    version_parts = version.split('.', 2)
    version_parts.extend(['0'] *  (3 - len(version_parts)))

    program = """
#include <wx/defs.h>
#include <wx/version.h>

int main()
{
    #if(wxCHECK_VERSION(%s, %s, %s))
        /* GOOD */
    #else
        #error "Invalid Version"
    #endif
}
""" % tuple(version_parts)
    
    ret = context.TryCompile(program, '.cpp')
    context.Result(ret)
    return ret


def ConfigureMHash(context, mhash_flags=''):
    """ Configure MHash and set the flags as needed. """
    
    # Merge flags
    if mhash_flags:
        context.env.MergeFlags(mhash_flags)
    else:
        context.env.MergeFlags('-lmhash')

    # Check for it's presence
    context.Message('Checking for mhash... ')

    program = """
#include <mhash.h>

int main(void)
{
    MHASH hash;
    hash = mhash_init(MHASH_MD5);

    return 0;
}
"""

    ret = context.TryLink(program, '.c')
    context.Result(ret)
    return ret
    


