from setuptools import setup, find_packages

install_requires = []

setup(name='heavy-profile',
      version="0.1",
      packages=find_packages(),
      description="Firefox Heavy Profile creator",
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      entry_points="""
      [console_scripts]
      hp-archiver = heavyprofile.archiver:main
      hp-creator = heavyprofile.creator:main
      hp-sync = heavyprofile.client:main
      """)
