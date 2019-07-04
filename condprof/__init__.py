try:
    from arsenic import connection
    from structlog import wrap_logger

    class NullLogger:
        def info(self, *args, **kw):
            pass

        def visit_url(self, index, total, url):
            print("%d/%d %s" % (index, total, url))

        def msg(self, event):
            print(event)

    logger = wrap_logger(NullLogger(), processors=[])
    connection.log = logger
except ImportError:
    logger = None
