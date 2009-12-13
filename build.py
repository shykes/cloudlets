from fabricate import *

def build():
    run("easy_install", "pip")
    run("pip", "install", "virtualenv==1.4.3")
    run("virtualenv", "env")
    run("./env/bin/pip",  "install", "-r", "requirements.txt")
    run("./env/bin/python", "setup.py", "install")

main()
