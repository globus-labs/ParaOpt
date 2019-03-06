from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
  install_requirements = f.readlines()

setup(
  name = "paropt",
  version = "0.1.0",
  author = "Ted Summer",
  author_email = "ted.summer2@gmail.com",
  description = ("Automates optimization of tools"),
  install_requires=install_requirements,
  packages=find_packages()
)