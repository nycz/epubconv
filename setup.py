from setuptools import setup, find_packages

setup(
    name='epubconv',
    version='0.1',
    description='Convert single or groups of files to an epub file',
    url='https://github.com/nycz/epubconv',
    author='nycz',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.5',
        'Topic :: Text Processing'
    ],
    keywords='epub ebooks',
    packages=find_packages(exclude=['docs']),
    install_requires=['jinja2>=2.8'],
    entry_points={
        'console_scripts': [
            'epubconv=epubconv.convert:run'
        ]
    }
)
