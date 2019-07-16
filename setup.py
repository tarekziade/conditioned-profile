from setuptools import setup, find_packages


install_requires = ["requests", "clint",
                    "cryptography"]


setup(name='conditioned-profile',
      version="0.1",
      packages=find_packages(),
      description="Firefox Heavy Profile creator",
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      entry_points="""
      [console_scripts]
      cp-creator = condprof.creator:main
      """)
