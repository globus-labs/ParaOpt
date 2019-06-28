from setuptools import setup, find_packages
# import pip
# import subprocess
# subprocess.call(["pip", "install", "-r", "requirements.txt"])


# def install(package):
#     if hasattr(pip, 'main'):
#         pip.main(['install', package])
#     else:
#         pip._internal.main(['install', package])


with open('requirements.txt', 'r') as f:
  install_requirements = f.readlines()

# for package in install_requirements:
# 	print(package)
# 	install(package)


setup(
	name = "paropt",
	version = "0.1.0",
	author = "Ted Summer",
	author_email = "ted.summer2@gmail.com",
	description = ("Automates optimization of tools"),
	install_requires=install_requirements,
	setup_requires=['bayesian-optimization'],
	dependency_links=["git+https://github.com/chaofengwu/BayesianOptimization.git"],
	packages=find_packages()
)