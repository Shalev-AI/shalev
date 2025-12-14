from setuptools import setup, find_packages

setup(
    name='shalev',
    version='0.1',
    package_dir={"": "src"},    # <--- tell setuptools where your packages are!
    packages=find_packages(where="src"),
    install_requires=[
        'click',
        'openai',
        'PyYAML',
        'yaspin'
        # ...other dependencies
    ],
    entry_points={
        'console_scripts': [
            'shalev=shalev.cli:main',  # shalev-cli, or whatever you want the command to be called
        ],
    },
)