from setuptools import setup, find_packages

from osfoffline import __version__


def parse_requirements(requirements):
    with open(requirements) as f:
        return [l.strip('\n') for l in f if l.strip('\n') and not l.startswith('#')]


requirements = parse_requirements('requirements.txt')

setup(
    name='osfoffline',
    version=__version__,
    # namespace_packages=['waterbutler', 'waterbutler.auth', 'waterbutler.providers'],
    description='OSF Offline Desktop Client',
    author='Center for Open Science',
    author_email='contact@cos.io',
    url='https://github.com/himanshuo/OSF-Offline',
    packages=find_packages(exclude=("tests*", )),
    package_dir={'osfoffline': 'osfoffline'},
    include_package_data=True,
    # install_requires=requirements,
    zip_safe=False,
    classifiers=[
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 0 - Development',
        # 'License :: OSI Approved :: Apache Software License',
    ],
)