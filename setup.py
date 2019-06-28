from setuptools import setup, find_packages
import pip


def install(package):
    if hasattr(pip, 'main'):
        pip.main(['install', package])
    else:
        pip._internal.main(['install', package])


with open('requirements.txt', 'r') as f:
  install_requirements = f.readlines()

for package in install_requirements:
	install(package)

setup(
  name = "paropt",
  version = "0.1.0",
  author = "Ted Summer",
  author_email = "ted.summer2@gmail.com",
  description = ("Automates optimization of tools"),
  # install_requires=install_requirements,
  packages=find_packages()
)