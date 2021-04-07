# Contributing to an Abilian open source project

## How to Contribute

This project is LGPL licensed and accepts contributions via Github pull requests. This document outlines resources and conventions useful for anyone wishing to contribute either by reporting issues or submitting pull requests.

More details [here](https://abilian-core.readthedocs.io/en/latest/contributing.html).

## Certificate of Origin

By contributing to any Abilian open source project you agree to its Developer Certificate of Origin (DCO), stated below. This document was created by the Linux Kernel community and is a simple statement that you, as a contributor, have the legal right to make the contribution.

~~~
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.
660 York Street, Suite 102,
San Francisco, CA 94110 USA

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
~~~

## Support Channels

Before opening a new issue, it's helpful to search the project - it's likely that another user
has already reported the issue you're facing, or it's a known issue that we're already aware of.


Our official support channels are:

- GitHub issues: https://github.com/abilian/abilian-core/issues
- Our mailing list: https://groups.google.com/g/abilian-users


## Getting Started

- Fork the repository on GitHub
- Read [the documentation](https://abilian-core.readthedocs.io/en/latest/contributing.html) for build instructions

## Contribution Flow

This is a rough outline of what a contributor's workflow looks like:

- Create a topic branch from where you want to base your work. This is usually master.
- Make commits of logical units.
- Make sure your commit messages are in the proper format, see below
- Push your changes to a topic branch in your fork of the repository.
- Submit a pull request

Thanks for your contributions!

### Design Documents

Most substantial changes should follow a [Design Document]()
describing the proposed changes and how they are tested and verified before they
are accepted into the project.

### Commit Style Guideline

We follow a rough convention for commit messages borrowed from CoreOS, who borrowed theirs
from AngularJS. This is an example of a commit:

    feat(scripts/test-cluster): add a cluster test command

    this uses tmux to setup a test cluster that you can easily kill and
    start for debugging.

To make it more formal, it looks something like this:


    {type}({scope}): {subject}
    <BLANK LINE>
    {body}
    <BLANK LINE>
    {footer}

The {scope} can be anything specifying place of the commit change.

The {subject} needs to use imperative, present tense: “change”, not “changed” nor
“changes”. The first letter should not be capitalized, and there is no dot (.) at the end.

Just like the {subject}, the message {body} needs to be in the present tense, and includes
the motivation for the change, as well as a contrast with the previous behavior. The first
letter in a paragraph must be capitalized.

All breaking changes need to be mentioned in the {footer} with the description of the
change, the justification behind the change and any migration notes required.

Any line of the commit message cannot be longer than 72 characters, with the subject line
limited to 50 characters. This allows the message to be easier to read on github as well
as in various git tools.

The allowed {types} are as follows:

    feat -> feature
    fix -> bug fix
    docs -> documentation
    style -> formatting
    ref -> refactoring code
    test -> adding missing tests
    chore -> maintenance

### More Details on Commits

For more details see the [commit style guide](https://abilian-developer-guide.readthedocs.io/en/latest/process.html#git).
