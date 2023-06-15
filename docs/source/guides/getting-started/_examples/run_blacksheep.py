# :lines: 11-

from reactpy import run
from reactpy.backend import blacksheep as blacksheep_server

# the run() function is the entry point for examples
blacksheep_server.configure = lambda _, cmpt: run(cmpt)


from blacksheep import Application

from reactpy import component, html
from reactpy.backend.blacksheep import configure


@component
def HelloWorld():
    return html.h1("Hello, world!")


app = Application()
configure(app, HelloWorld)
