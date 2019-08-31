import os
import sys
import json
import globus_sdk
from configobj import ConfigObj
from paropt_sdk import version

__all__ = (
    # option name constants
    'PAROPT_RT_OPTNAME',
    'PAROPT_AT_OPTNAME',
    'PAROPT_AT_EXPIRES_OPTNAME',

    'write_option',
    'lookup_option',
    'remove_option',
    'internal_auth_client',

    'check_logged_in',
    'safeprint',
    'format_output'
)

# The path to read and write servable definitions.
PAROPT_SERVICE_DOMAIN = os.getenv('PAROPT_SERVICE_DOMAIN') or '35.168.128.54'
PAROPT_SERVICE_ADDRESS = f'https://{PAROPT_SERVICE_DOMAIN}:8080/api/v1'

CONF_SECTION_NAME = 'paropt'

# client id for paropt NATIVE application
CLIENT_ID = '805f14ef-0699-4e1f-801e-96919f64d0a7'
PAROPT_RT_OPTNAME = 'paropt_refresh_token'
PAROPT_AT_OPTNAME = 'paropt_access_token'
PAROPT_AT_EXPIRES_OPTNAME = 'paropt_access_token_expires'

GLOBUS_ENV = os.environ.get('GLOBUS_SDK_ENVIRONMENT')
# if GLOBUS_ENV:
#     FUNCX_RT_OPTNAME = '{}_{}'.format(GLOBUS_ENV, FUNCX_RT_OPTNAME)
#     FUNCX_AT_OPTNAME = '{}_{}'.format(GLOBUS_ENV, FUNCX_AT_OPTNAME)
#     FUNCX_AT_EXPIRES_OPTNAME = '{}_{}'.format(GLOBUS_ENV,
#                                                FUNCX_AT_EXPIRES_OPTNAME)
#     CLIENT_ID = {
#         'sandbox':      'f9e36a20-2e1a-49e5-ba67-34cc82ca8b29',
#         'test':         '2aa543de-b6c6-4aa5-9d7b-ef28e3a28cd8',
#         'staging':      '0811fdd3-0d3e-4b5e-b634-8d6c91d87f21',
#         'preview':      '988ff3e0-3bcf-495a-9f12-3b3a309bdb36',
#     }.get(GLOBUS_ENV, CLIENT_ID)


def get_config_obj(file_error=False):
    path = os.path.expanduser("~/.globus.cfg")

    return ConfigObj(path, encoding='utf-8', file_error=file_error)


def lookup_option(option):
    conf = get_config_obj()
    try:
        return conf[CONF_SECTION_NAME][option]
    except KeyError:
        return None


def write_option(option, value):
    """
    Write an option to disk -- doesn't handle config reloading
    """
    # deny rwx to Group and World -- don't bother storing the returned old mask
    # value, since we'll never restore it in the CLI anyway
    # do this on every call to ensure that we're always consistent about it
    os.umask(0o077)

    conf = get_config_obj()

    # add the section if absent
    if CONF_SECTION_NAME not in conf:
        conf[CONF_SECTION_NAME] = {}

    conf[CONF_SECTION_NAME][option] = value
    conf.write()


def remove_option(option):
    conf = get_config_obj()

    # if there's no section for the option we're removing, just return None
    try:
        section = conf[CONF_SECTION_NAME]
    except KeyError:
        return None

    try:
        opt_val = section[option]

        # remove value and flush to disk
        del section[option]
        conf.write()
    except KeyError:
        opt_val = None

    # return the just-deleted value
    return opt_val


def internal_auth_client():
    """
    Get the globus native app client.

    :return:
    """
    return globus_sdk.NativeAppAuthClient(CLIENT_ID, app_name=version.app_name)


def check_logged_in():
    """
    Check if the user is already logged in.

    :return:
    """
    search_rt = lookup_option(PAROPT_RT_OPTNAME)
    if search_rt is None:
        return False
    native_client = internal_auth_client()
    res = native_client.oauth2_validate_token(search_rt)
    return res['active']

def safeprint(s):
    """
    Catch print errors.

    :param s:
    :return:
    """
    try:
        print(s)
        sys.stdout.flush()
    except IOError:
        pass

def format_output(dataobject):
    """
    Use safe print to make sure jobs are correctly printed.

    :param dataobject:
    :return:
    """
    safeprint(json.dumps(dataobject, indent=2, separators=(',', ': ')))
