Conditioned Profile
===================

This project provides a command-line tool (**cp-creator**) that can be
used to generate a collection of profiles. It's based on Arsenic but
might move to Selenium to make its integration easier.

The tool creates a webdriver session and browses the web using a scenario.

A scenario is a single Python module that implements a coroutine and
get registered in the system.

If you want to create a new scenario, you can get started by looking at
the `heavy scenario <https://github.com/tarekziade/conditioned-profile/blob/master/condprof/scenario/heavy.py#L57>`_

