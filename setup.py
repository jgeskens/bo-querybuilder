#!/usr/bin/env python
from setuptools import setup, find_packages
import querybuilder

setup(
    name="bo-querybuilder",
    version=querybuilder.__version__,
    url='https://github.com/jgeskens/bo-querybuilder',
    license='MIT',
    description="QueryBuilder Backoffice View for Django Advanced Reports",
    long_description=open('README.md', 'r').read(),
    author='Jef Geskens, VikingCo nv',
    packages=find_packages('.'),
    package_data = {'querybuilder': [
                'static/*.js', 'static/*/*.js', 'static/*/*/*.js',
                'static/*.css', 'static/*/*.css', 'static/*/*/*.css',
                'static/*.png', 'static/*/*.png', 'static/*/*/*.png', 'static/*/*/*/*.png',
		'static/*.html', 'static/*/*.html', 'static/*/*/*.html', 'static/*/*/*/*.html',
                'templates/*.html', 'templates/*/*.html', 'templates/*/*/*.html', 'templates/*/*/*/*.html',
                ],},
    zip_safe=False, # Don't create egg files, Django cannot find templates in egg files.
    include_package_data=True,
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Environment :: Web Environment',
        'Framework :: Django',
    ],
)
