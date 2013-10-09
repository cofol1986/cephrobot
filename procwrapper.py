
def subproc_call(*args, **kwargs):
    """
    call subproc that might fail, collect returncode and stderr/stdout
    to be used in pushy.compile()d functions.  Returns 4-tuple of
    (process exit code, command, stdout contents, stderr contents)
    """
    import subprocess
    import tempfile

    otmp = tempfile.TemporaryFile()
    etmp = tempfile.TemporaryFile()
    cmd = ' '.join(kwargs['args'])
    ret = 0
    errtxt = ''
    kwargs.update(dict(stdout=otmp, stderr=etmp))
    try:
        subprocess.check_call(*args, **kwargs)
    except subprocess.CalledProcessError as e:
        ret = e.returncode
    except Exception as e:
        ret = -1
        # OSError has errno
        if hasattr(e, 'errno'):
            ret = e.errno
        errtxt = str(e)
    otmp.seek(0)
    etmp.seek(0)
    return (ret, cmd, otmp.read(), errtxt + etmp.read())
