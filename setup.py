from setuptools import setup, find_packages
# import pip
# import subprocess
# subprocess.call(["pip", "install", "-r", "requirements.txt"])


# def install(package):
#     if hasattr(pip, 'main'):
#         pip.main(['install', package])
#     else:
#         pip._internal.main(['install', package])


# with open('requirements.txt', 'r') as f:
#   install_requirements = f.readlines()

# for package in install_requirements:
# 	print(package)
# 	install(package)


# from setuptools import setup
from setuptools.extension import Extension
import sys


def get_requirements(remove_links=True):
    """
    lists the requirements to install.
    """
    requirements = []
    try:
        with open('requirements.txt') as f:
            requirements = f.read().splitlines()
    except Exception as ex:
        with open('DecoraterBotUtils.egg-info\requires.txt') as f:
            requirements = f.read().splitlines()
    if remove_links:
        for requirement in requirements:
        # git repository url.
	        if requirement.startswith("git+"):
	            requirements.remove(requirement)
	        # subversion repository url.
	        if requirement.startswith("svn+"):
	            requirements.remove(requirement)
	        # mercurial repository url.
	        if requirement.startswith("hg+"):
	            requirements.remove(requirement)
    return requirements


def get_links():
    """
    gets URL Dependency links.
    """
    links_list = get_requirements(remove_links=False)
    for link in links_list:
        keep_link = False
        already_removed = False
        # git repository url.
        if not link.startswith("git+"):
            if not link.startswith("svn+"):
                if not link.startswith("hg+"):
                    links_list.remove(link)
                    already_removed = True
                else:
                    keep_link = True
                if not keep_link and not already_removed:
                    links_list.remove(link)
                    already_removed = True
            else:
                keep_link = True
            if not keep_link and not already_removed:
                links_list.remove(link)
    return links_list


def get_version():
    """
    returns version.
    """
    return '0.0.1'


def get_extensions():
    """
    lists the extensions to build with an compiler.
    """
    if sys.platform != 'cygwin':
        BotErrors = Extension(
            'DecoraterBotUtils.BotErrors', [
                'DecoraterBotUtils/BotErrors.c'])
    else:
        BotErrors = Extension(
            'DecoraterBotUtils.BotErrors',
            library_dirs=['/usr/local/bin'],
            sources=['DecoraterBotUtils/BotErrors.c'])
    return [BotErrors]


if not get_version():
    raise RuntimeError('version is not set')

try:
    with open('README.rst') as f:
        readme = f.read()
except FileNotFoundError:
    readme = ""

setup(
	name = "paropt",
	version = "0.1.0",
	author = "Ted Summer",
	author_email = "ted.summer2@gmail.com",
	description = ("Automates optimization of tools"),
	# install_requires=install_requirements,
	install_requires=get_requirements(),
	dependency_links=get_links(),
	packages=find_packages()
)