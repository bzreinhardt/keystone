import requests
from credentials import credentials

key = credentials['meaningcloud']['password']
url = credentials['meaningcloud']['url']

text = """
Um
so
we
've got our opening , our our agenda is the opening , uh acquaintance which we'
ve
kinda
done.Uh
tool
training, project
plan
discussion and then
closing.Uh
grand
total
of
twenty
five
minutes
we
have
here.Um
so
we
are
putting
together
a
new
remote
control.Um
we
want
it
to
be
something
original.Um
of
course
we
're a not only a electronics company but a fashion um conscious electronics company , so we want it to be trendy um and we want it to be easy to use . Um we'
ve
got
the
functional
design, conceptual
design and detailed
design
um
which
basically is is the
three
of
you
um.And
w
uh
well
um
functional
design
um.Um
do
we
have
um
any
ideas
of
of
maybe
d
let
's just throw out some ideas of what kind of remote control we want to have , and then we can go into how we'
re
gonna
design
it and and how
we
're gonna do the detailing on it .
"""

payload = "key=%s&lang=en&txt=%s&tt=a" % (key, text)
headers = {'content-type': 'application/x-www-form-urlencoded'}

response = requests.request("POST", url, data=payload, headers=headers)

print(response.text)
with open('response.json', 'w') as f:
    f.write(response.text)